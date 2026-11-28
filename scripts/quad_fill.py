# SPDX-License-Identifier: GPL-3.0-or-later
"""Fill holes with quads, choosing the topology from the edge count of each side.

Like Grid Fill, but the two opposite sides of the hole don't need the same
number of edges. The script finds the 4 corners of the hole, counts the edges
on each side and builds the fill from straight strips of quads joined by the
classic transition rows (as on the usual topology cheat sheets):

    3-1, 4-2, 5-3, ...  drop 2 edges: the two outer columns turn into the
                        sides, the inner columns run straight on into a band
                        of trapezoids
    1-2, 2-3, 3-4, ...  drop 1 edge where one side has an extra edge: a split
                        under the middle edge, with an edge running across to
                        that side

Columns line up with the vertices of the side they come from and rows with
the vertices of the sides they run between, then everything is mapped onto
the surface spanned by the border, so it follows the curve of the hole.

A hole with an odd total number of edges can't be filled with quads only, so
it gets exactly one triangle (or is skipped, see ALLOW_TRIANGLE).

Run from Blender's Text Editor (Run Script) in Edit Mode, with the boundary
edges of one or more holes selected (Alt+click the hole's edge loop). It fills
each hole once, selects the new faces and registers nothing.

Rotation: each hole has a few layouts (the pattern rotated or mirrored, or its
changing rows moved toward the other side); the console prints "layout 2/6"
and so on. With LAYOUT = 0, running the script again while the new faces are
still selected re-fills the hole with the next layout, so you can cycle. Set
LAYOUT to a number to always use that layout (it also re-fills selected
faces with it); numbers past the last layout wrap around.
"""

import itertools
import math

import bmesh
import bpy
from mathutils import Vector

# Settings. Edit these, then run the script again.
LAYOUT = 0               # rotation: 0 = best first, re-run on the new faces for the next;
                         # 1, 2, 3, ... = always use that layout
ALLOW_TRIANGLE = True    # odd edge count: True = one triangle, False = skip that hole
FALLBACK_FILL = True     # sides too uneven for the patterns: True = triangle fill
                         # joined into quads where possible, False = skip

BALANCE_WEIGHT = 0.5     # corner choice: sharp corners first, then even sides
MAX_LAYOUTS_TRIED = 50   # layouts checked for folded or flat faces before falling back


# --- Finding the holes ------------------------------------------------------

def boundary_loops(edges):
    """Order the given open-border edges into closed vertex loops.

    Returns (loops, skipped): loops are lists of BMVerts in order, skipped
    counts edge chains that are not simple closed loops.
    """
    links = {}
    for edge in edges:
        for vert in edge.verts:
            links.setdefault(vert, []).append(edge)
    loops, skipped, seen = [], 0, set()
    for start in edges:
        if start in seen:
            continue
        chain, ok = [start.verts[0]], True
        edge, vert = start, start.verts[1]
        seen.add(start)
        while vert is not chain[0]:
            if len(links[vert]) != 2:
                ok = False
                break
            chain.append(vert)
            edge = links[vert][0] if links[vert][1] is edge else links[vert][1]
            if edge in seen:
                ok = False
                break
            seen.add(edge)
            vert = edge.other_vert(vert)
        if ok and len(links[chain[0]]) == 2 and len(chain) >= 3:
            loops.append(chain)
        else:
            skipped += 1
            # Mark the rest of this chain as seen so it is reported once.
            stack = [start]
            while stack:
                for v in stack.pop().verts:
                    for e in links[v]:
                        if e not in seen:
                            seen.add(e)
                            stack.append(e)
    return loops, skipped


def turning_angles(coords):
    """How sharply the loop turns at each vertex (0 = straight on)."""
    n = len(coords)
    out = []
    for i in range(n):
        before = coords[i] - coords[i - 1]
        after = coords[(i + 1) % n] - coords[i]
        if before.length < 1e-12 or after.length < 1e-12:
            out.append(0.0)
        else:
            out.append(before.angle(after))
    return out


# --- Choosing a layout (pure Python, no Blender data) ----------------------

def plan_rows(bottom, right, top, left, allow_triangle=ALLOW_TRIANGLE, place="middle"):
    """Rows of a 4-sided patch, from the bottom side up, or None if not possible.

    Arguments are edge counts. Needs bottom >= top, right >= left and
    bottom - top >= right - left (choose_layout tries every orientation).
    Row kinds: "grid" (same width), "shrink2" (width - 2, the 3-to-1 pattern),
    "corner" (width - 1, uses 2 edges of the right side), "triangle"
    (width - 1 with one triangle). Every row uses 1 edge of the left side.
    place puts the changing rows in the "middle", at the "start" (next to the
    bottom side) or at the "end" (next to the top side).
    """
    across, up = bottom - top, right - left
    if across < 0 or up < 0 or across < up:
        return None
    triangle = (across - up) % 2
    if triangle and not allow_triangle:
        return None
    shrink2 = (across - up - triangle) // 2
    grid = left - shrink2 - up - triangle
    if grid < 0:
        return None
    lower = {"middle": grid // 2, "start": 0, "end": grid}[place]
    return (["grid"] * lower + ["shrink2"] * shrink2 + ["corner"] * up
            + ["triangle"] * triangle + ["grid"] * (grid - lower))


def oriented_sides(n, corners, reverse, start):
    """The 4 sides as lists of loop indices: bottom and top left to right,
    right and left bottom to top."""
    c = sorted(corners)
    sides = []
    for k in range(4):
        a, b = c[k], c[(k + 1) % 4]
        sides.append([(a + i) % n for i in range((b - a) % n + 1)])
    if reverse:
        sides = [side[::-1] for side in reversed(sides)]
    bottom, right, top, left = (sides[(start + k) % 4] for k in range(4))
    return bottom, right, top[::-1], left[::-1]


def candidate_layouts(angles, allow_triangle=ALLOW_TRIANGLE, balance_weight=BALANCE_WEIGHT):
    """Every way to pick 4 corners and an orientation that the row patterns
    can fill, best first: sharp corners, then sides of even length.

    Each layout is (bottom, right, top, left, rows).
    """
    n = len(angles)
    if n < 4:
        return []
    if n <= 24:
        candidates = range(n)
    else:  # the sharpest vertices, plus evenly spaced ones for smooth loops
        sharpest = sorted(range(n), key=lambda i: -angles[i])[:12]
        candidates = sorted(set(sharpest) | {round(k * n / 16) % n for k in range(16)})
    found = []
    for corners in itertools.combinations(candidates, 4):
        counts = [(corners[(k + 1) % 4] - corners[k]) % n for k in range(4)]
        imbalance = sum(abs(c - n / 4) for c in counts) / n
        score = sum(angles[i] for i in corners) - balance_weight * imbalance
        for reverse, start in itertools.product((False, True), range(4)):
            sides = oriented_sides(n, corners, reverse, start)
            rows = plan_rows(*(len(s) - 1 for s in sides), allow_triangle=allow_triangle)
            if rows is not None:
                found.append((-score, len(found), (*sides, rows)))
                break
    return [layout for _, _, layout in sorted(found)]


def layout_variants(n, layout, allow_triangle=ALLOW_TRIANGLE):
    """The other ways to fill the same 4 corners: every orientation (rotated
    and mirrored) and every place for the changing rows. layout comes first;
    variants that give the same faces are left out."""
    bottom, right, top, _ = layout[:4]
    corners = sorted({bottom[0], bottom[-1], top[0], top[-1]})
    out, seen = [], set()
    options = [layout] + [
        (*sides, rows)
        for reverse, start in itertools.product((False, True), range(4))
        for sides in [oriented_sides(n, corners, reverse, start)]
        for place in ("middle", "start", "end")
        for rows in [plan_rows(*(len(s) - 1 for s in sides), allow_triangle=allow_triangle,
                               place=place)]
        if rows is not None]
    for option in options:
        faces, _ = layout_faces(*option, first_new=n)
        key = signature(faces, n)
        if key not in seen:
            seen.add(key)
            out.append(option)
    return out


def signature(faces, n):
    """What a fill looks like from its border: which border vertices each face
    uses. Tells the variants apart, and recognises an existing fill."""
    return tuple(sorted(tuple(sorted(i for i in face if i < n)) for face in faces))


def choose_layout(angles, allow_triangle=ALLOW_TRIANGLE, balance_weight=BALANCE_WEIGHT):
    """The best layout from candidate_layouts, or None."""
    layouts = candidate_layouts(angles, allow_triangle, balance_weight)
    return layouts[0] if layouts else None


class Polyline:
    """A side of the hole, sampled by arc length from 0 to 1."""

    def __init__(self, points):
        self.points = points
        self.cum = [0.0]
        for a, b in zip(points, points[1:]):
            self.cum.append(self.cum[-1] + (b - a).length)
        total = self.cum[-1]
        self.params = ([c / total for c in self.cum] if total > 1e-12
                       else [i / (len(points) - 1) for i in range(len(points))])

    def at(self, t):
        params = self.params
        for i in range(len(params) - 1):
            if t <= params[i + 1] or i == len(params) - 2:
                span = params[i + 1] - params[i]
                f = 0.0 if span < 1e-12 else min(max((t - params[i]) / span, 0.0), 1.0)
                return self.points[i].lerp(self.points[i + 1], f)
        return self.points[-1].copy()


def border_uv(sides, params):
    """Square coordinates of the border vertices: bottom v=0, right u=1,
    top v=1, left u=0, spaced like the vertices along each side."""
    uv = {}
    for i, t in zip(sides[0], params[0]):
        uv[i] = (t, 0.0)
    for i, t in zip(sides[1], params[1]):
        uv[i] = (1.0, t)
    for i, t in zip(sides[2], params[2]):
        uv[i] = (t, 1.0)
    for i, t in zip(sides[3], params[3]):
        uv[i] = (0.0, t)
    return uv


def layout_faces(bottom, right, top, left, rows, first_new, uv=None):
    """Faces of the patch as tuples of vertex ids, and where the new vertices go.

    Ids below first_new are loop indices (the border); new vertices get ids
    from first_new up. uv holds the square coordinates of the border vertices
    (see border_uv; evenly spaced if None). Returns (faces, new_uv), new_uv[i]
    being the square coordinates of vertex first_new + i.

    Below the changing rows the columns run straight up from the bottom
    side's vertices, above them straight down from the top side's; every row
    line runs straight across from a left side vertex to a right side vertex.
    """
    sides = (bottom, right, top, left)
    if uv is None:
        uv = border_uv(sides, [[i / (len(s) - 1) for i in range(len(s))] for s in sides])
    uv = dict(uv)
    new_uv = []
    faces = []

    def new_vert(u, v):
        new_uv.append((u, v))
        uv[first_new + len(new_uv) - 1] = (u, v)
        return first_new + len(new_uv) - 1

    def mid(a, b):
        return new_vert((uv[a][0] + uv[b][0]) / 2, (uv[a][1] + uv[b][1]) / 2)

    def v_on(line, u):
        """Height of a row line at u."""
        for a, b in zip(line, line[1:]):
            (ua, va), (ub, vb) = uv[a], uv[b]
            if u <= ub or b == line[-1]:
                f = 0.0 if ub - ua < 1e-12 else min(max((u - ua) / (ub - ua), 0.0), 1.0)
                return va + (vb - va) * f
        return uv[line[-1]][1]

    changing = [k for k, kind in enumerate(rows) if kind != "grid"]
    bottom_u = [uv[i][0] for i in bottom]
    top_u = [uv[i][0] for i in top]

    def line_u(j, width):
        """u of the vertices on row line j (0 = the bottom side)."""
        if not changing:
            f = j / len(rows)
            return [a + (b - a) * f for a, b in zip(bottom_u, top_u)]
        if j <= changing[0]:
            return bottom_u
        if j > changing[-1]:
            return top_u
        return [i / width for i in range(width + 1)]

    line, li, ri = list(bottom), 0, 0
    for row, kind in enumerate(rows):
        w = len(line) - 1
        r = 2 if kind == "corner" else 1
        width = w - {"grid": 0, "shrink2": 2, "corner": 1, "triangle": 1}[kind]
        if row == len(rows) - 1:
            nxt = list(top)
        else:
            lv, rv = left[li + 1], right[ri + r]
            us = line_u(row + 1, width)
            vl, vr = uv[lv][1], uv[rv][1]
            nxt = [lv] + [new_vert(us[i], vl + (vr - vl) * us[i]) for i in range(1, width)] + [rv]
        b, t = line, nxt

        def straight(i, j):
            faces.append((b[i], b[i + 1], t[j + 1], t[j]))

        if kind == "grid":
            for i in range(w):
                straight(i, i)
        elif kind == "shrink2":
            # 3 to 1, 4 to 2, 5 to 3, ...: the two outer bottom columns turn
            # into the sides, the inner ones run up to a line of new vertices,
            # and a band of trapezoids joins that line to the top.
            inner = []
            for i in range(1, w):
                u = uv[b[i]][0]
                inner.append(new_vert(u, (uv[b[i]][1] + v_on(t, u)) / 2))
            faces.append((b[0], b[1], inner[0], t[0]))
            for i in range(1, w - 1):
                faces.append((b[i], b[i + 1], inner[i], inner[i - 1]))
            faces.append((b[w - 1], b[w], t[width], inner[-1]))
            for j in range(width):
                faces.append((inner[j], inner[j + 1], t[j + 1], t[j]))
        elif kind == "corner":
            # 1 to 2, 2 to 3, ...: a split under the middle top edge, with an
            # edge running across to the extra vertex on the right side.
            k = width // 2
            for i in range(k):
                straight(i, i)
            x = mid(t[k], b[k + 1])
            splits = [mid(b[i], t[i - 1]) for i in range(k + 2, w)] + [right[ri + 1]]
            faces += [(b[k], b[k + 1], x, t[k]), (b[k + 1], b[k + 2], splits[0], x),
                      (x, splits[0], t[k + 1], t[k])]
            for n, i in enumerate(range(k + 2, w)):
                s0, s1 = splits[n], splits[n + 1]
                faces += [(b[i], b[i + 1], s1, s0), (s0, s1, t[i], t[i - 1])]
        else:  # triangle: an odd edge count leaves one, in the middle
            k = width // 2
            for i in range(k):
                straight(i, i)
            faces.append((b[k], b[k + 1], t[k]))
            for i in range(k + 1, w):
                straight(i, i - 1)
        line, li, ri = nxt, li + 1, ri + r
    return faces, new_uv


def build_patch(coords, sides, rows):
    """Faces and new vertex positions for a layout: the square coordinates
    from layout_faces mapped onto the Coons patch spanned by the 4 sides, so
    the fill follows the curvature of the hole's border."""
    curves = [Polyline([coords[i] for i in s]) for s in sides]
    uv = border_uv(sides, [c.params for c in curves])
    faces, new_uv = layout_faces(*sides, rows, first_new=len(coords), uv=uv)
    bottom, right, top, left = curves
    c00, c10, c01, c11 = bottom.at(0.0), bottom.at(1.0), top.at(0.0), top.at(1.0)
    positions = [(1 - v) * bottom.at(u) + v * top.at(u) + (1 - u) * left.at(v) + u * right.at(v)
                 - ((1 - u) * (1 - v) * c00 + u * (1 - v) * c10 + (1 - u) * v * c01 + u * v * c11)
                 for u, v in new_uv]
    return faces, positions


def face_normal(points):
    """Area-weighted normal (Newell's method); its length is twice the area."""
    normal = Vector()
    for a, b in zip(points, points[1:] + points[:1]):
        normal += a.cross(b)
    return normal


def is_clean(points, faces):
    """No degenerate face and no face bent more than about 70 degrees
    against a neighbour (a fold or a sliver standing on the border)."""
    normals = [face_normal([points[i] for i in face]) for face in faces]
    mean_area = sum(n.length for n in normals) / len(normals)
    if mean_area < 1e-12 or any(n.length < 1e-3 * mean_area for n in normals):
        return False
    edge_faces = {}
    for k, face in enumerate(faces):
        for a, b in zip(face, face[1:] + face[:1]):
            edge_faces.setdefault(frozenset((a, b)), []).append(k)
    return all(len(ks) == 1 or normals[ks[0]].normalized().dot(normals[ks[1]].normalized()) > 0.35
               for ks in edge_faces.values())


# --- Filling ----------------------------------------------------------------

def match_neighbours(loop_verts, new_faces, old_faces):
    """Copy material and shading from the surrounding faces and make the
    normals agree with them."""
    for a, b in zip(loop_verts, loop_verts[1:] + loop_verts[:1]):
        edge = next((e for e in a.link_edges if e.other_vert(a) is b), None)
        if edge is None:
            continue
        old = [f for f in edge.link_faces if f in old_faces]
        new = [f for f in edge.link_faces if f in new_faces]
        if not old or not new:
            continue
        flip = next(l.vert for l in old[0].loops if l.edge is edge) is \
            next(l.vert for l in new[0].loops if l.edge is edge)
        return old[0].material_index, old[0].smooth, flip
    return None, None, False


def fill_loop(bm, loop_verts, allow_triangle=ALLOW_TRIANGLE, fallback=FALLBACK_FILL,
              current=None, layout=LAYOUT):
    """Fill one closed boundary loop.

    layout > 0 picks that variant (1-based, wrapping). With layout 0, current
    is the signature of the fill the hole had before (when cycling) and the
    variant after it is used, or the best one if there was none. Returns (new faces, how, variant, variants),
    where how is "quads", "triangle", "fallback" or "skipped" and variant is
    the 1-based number of the layout used out of variants.
    """
    coords = [v.co.copy() for v in loop_verts]
    old_faces = {f for v in loop_verts for f in v.link_faces}
    n = len(loop_verts)

    def attempt(layout):
        *sides, rows = layout
        faces, positions = build_patch(coords, sides, rows)
        return (rows, faces, positions) if is_clean(coords + positions, faces) else None

    chosen, variant, variants = None, 0, 0
    for candidate in candidate_layouts(turning_angles(coords), allow_triangle)[:MAX_LAYOUTS_TRIED]:
        chosen = attempt(candidate)
        if chosen is None:
            continue
        options = layout_variants(n, candidate, allow_triangle)
        keys = [signature(layout_faces(*o, first_new=n)[0], n) for o in options]
        if layout > 0:
            first = (layout - 1) % len(options)
        else:
            first = (keys.index(current) + 1) % len(options) if current in keys else 0
        for step in range(len(options)):
            k = (first + step) % len(options)
            result = chosen if k == 0 else attempt(options[k])
            if result is not None:
                chosen, variant, variants = result, k + 1, len(options)
                break
        break
    if chosen is None:
        if not fallback or len(loop_verts) < 3:
            return [], "skipped", 0, 0
        edges = [e for a, b in zip(loop_verts, loop_verts[1:] + loop_verts[:1])
                 for e in a.link_edges if e.other_vert(a) is b]
        tris = bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=edges)["geom"]
        tris = [f for f in tris if isinstance(f, bmesh.types.BMFace)]
        joined = bmesh.ops.join_triangles(bm, faces=tris, angle_face_threshold=math.pi,
                                          angle_shape_threshold=math.pi)["faces"]
        new_faces = set(joined) | {f for f in tris if f.is_valid}
        how = "fallback"
    else:
        rows, faces, positions = chosen
        verts = list(loop_verts) + [bm.verts.new(p) for p in positions]
        new_faces = {bm.faces.new([verts[i] for i in face]) for face in faces}
        how = "triangle" if "triangle" in rows else "quads"

    material, smooth, flip = match_neighbours(loop_verts, new_faces, old_faces)
    if flip:
        bmesh.ops.reverse_faces(bm, faces=list(new_faces))
    for face in new_faces:
        if material is not None:
            face.material_index, face.smooth = material, smooth
        face.select_set(True)
    return list(new_faces), how, variant, variants


def face_regions(faces):
    """Split faces into groups connected through shared edges."""
    todo, regions = set(faces), []
    while todo:
        stack, region = [todo.pop()], set()
        while stack:
            face = stack.pop()
            region.add(face)
            for edge in face.edges:
                for other in edge.link_faces:
                    if other in todo:
                        todo.remove(other)
                        stack.append(other)
        regions.append(region)
    return regions


def clear_fill(bm, region):
    """Remove a filled region, keeping its border. Returns (border loop,
    signature of the removed fill) or None if the border isn't one loop."""
    border = [e for f in region for e in f.edges
              if sum(g in region for g in e.link_faces) == 1]
    loops, bad = boundary_loops(list(set(border)))
    if bad or len(loops) != 1:
        return None
    loop = loops[0]
    index = {v: i for i, v in enumerate(loop)}
    key = tuple(sorted(tuple(sorted(index[v] for v in f.verts if v in index)) for f in region))
    inner_verts = {v for f in region for v in f.verts if v not in index}
    inner_edges = {e for f in region for e in f.edges if e not in border}
    bmesh.ops.delete(bm, geom=list(region), context='FACES_ONLY')
    bmesh.ops.delete(bm, geom=list(inner_verts), context='VERTS')
    bmesh.ops.delete(bm, geom=[e for e in inner_edges if e.is_valid], context='EDGES')
    return loop, key


def quad_fill(obj, allow_triangle=ALLOW_TRIANGLE, fallback=FALLBACK_FILL, layout=LAYOUT):
    """Fill every hole whose border is selected on obj (in Edit Mode).

    If faces are selected instead (for example the fill this script just
    made), each group of selected faces is filled again: with layout 0 using
    the next variant, so running the script repeatedly cycles through
    rotations, otherwise with variant number layout.

    Returns a dict counting holes by how they were filled, plus "faces"
    (new faces in total), "not_loops" (selections that aren't one closed
    loop), "cycled" (True when faces were re-filled) and "variants" (a list
    of (variant, variants) per hole).
    """
    bm = bmesh.from_edit_mesh(obj.data)
    stats = {"quads": 0, "triangle": 0, "fallback": 0, "skipped": 0, "faces": 0,
             "not_loops": 0, "variants": []}
    selected_faces = [f for f in bm.faces if f.select]
    stats["cycled"] = bool(selected_faces)
    if selected_faces:
        jobs = []
        for region in face_regions(selected_faces):
            cleared = clear_fill(bm, region)
            if cleared is None:
                stats["not_loops"] += 1
            else:
                jobs.append(cleared)
    else:
        edges = [e for e in bm.edges if e.select and len(e.link_faces) <= 1]
        loops, stats["not_loops"] = boundary_loops(edges)
        jobs = [(loop, None) for loop in loops]
    for loop, current in jobs:
        faces, how, variant, variants = fill_loop(bm, loop, allow_triangle, fallback, current, layout)
        stats[how] += 1
        stats["faces"] += len(faces)
        if variants:
            stats["variants"].append((variant, variants))
    bm.select_flush_mode()
    bmesh.update_edit_mesh(obj.data)
    return stats


if __name__ == "__main__":
    obj = bpy.context.edit_object
    if obj is None or obj.type != 'MESH':
        print("quad_fill: enter Edit Mode on a mesh and select the border of a hole")
    else:
        s = quad_fill(obj)
        holes = s["quads"] + s["triangle"] + s["fallback"]
        layouts = ", ".join(f"{v}/{n}" for v, n in s["variants"]) or "-"
        print(f"quad_fill: {'re-filled' if s['cycled'] else 'filled'} {holes} hole(s) with"
              f" {s['faces']} faces, layout {layouts}"
              f" ({s['triangle']} with one triangle, {s['fallback']} by triangle fill),"
              f" skipped {s['skipped'] + s['not_loops']}."
              + (" Run again for the next layout." if LAYOUT == 0 else f" LAYOUT = {LAYOUT}."))
