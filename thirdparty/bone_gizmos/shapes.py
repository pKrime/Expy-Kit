import bpy

from math import pi, cos, sin, sqrt

from copy import deepcopy
import numpy as np

from enum import Enum

class Axis(Enum):
	X = 0
	Y = 1
	Z = 2

class BasicShape:
	vertices = []

	def __init__(self, scale=1.0, offset=(0.0, 0.0)):
		# make vertices unique to instance
		self.vertices = deepcopy(self.vertices)
		self.scale(scale)
		self.offset(offset)
		self.center()

	def scale(self, factor):
		for verts in self.vertices:
			for i, co in enumerate(verts):
				verts[i] = co * factor

	def offset(self, offset):
		for verts in self.vertices:
			for i, co in enumerate(verts):
				verts[i] = co + offset[i]

	@property
	def size(self):
		# TODO
		return 1.0, 1.0

	def center(self):
		size_x, size_y = self.size
		self.offset((size_x/-2.0, size_y/-2.0))


class Tris2D(BasicShape):
	vertices = [
		[0.0, 0.0],
		[0.0, 1.0],
		[1.0, 1.0],
	]


class Quad2D(BasicShape):
	vertices = deepcopy(Tris2D.vertices) + [deepcopy(Tris2D.vertices[-1]),
											[Tris2D.vertices[-1][0], Tris2D.vertices[0][1]],
											deepcopy(Tris2D.vertices[0])]

	@property
	def size(self):
		low_left = self.vertices[0]
		up_right = self.vertices[2]
		return abs(up_right[0] - low_left[0]), abs(up_right[1] - low_left[1])

	def frame_vertices(self, thickness=0.25):
		inner = Quad2D(scale=1 - thickness)
		inner.center()

		verts = []
		for i in range(0, 4, 3):
			verts.append(self.vertices[i])
			verts.append(self.vertices[i + 1])
			verts.append(inner.vertices[i])

			verts.append(inner.vertices[i])
			verts.append(inner.vertices[i + 1])
			verts.append(self.vertices[i + 1])

			verts.append(self.vertices[i + 1])
			verts.append(self.vertices[i + 2])
			verts.append(inner.vertices[i + 1])

			verts.append(inner.vertices[i + 1])
			verts.append(inner.vertices[i + 2])
			verts.append(self.vertices[i + 2])

		return verts


class Rect2D(BasicShape):
	# Coordinates (each one is a triangle).
	vertices = [
		[-0.5, -1.0],
		[-0.5, 1.0],
		[0.5, 1.0],

		[0.5, 1.0],
		[0.5, -1.0],
		[-0.5, -1.0],
	]


class Cross2D(BasicShape):
	vertices = deepcopy(Rect2D.vertices) + [
		[-1.0, -0.5],
		[-1.0, 0.5],
		[1.0, 0.5],

		[1.0, 0.5],
		[1.0, -0.5],
		[-1.0, -0.5],
	]


class Circle2D(BasicShape):
	def __init__(self, scale=1.0, offset=(0.0, 0.0), segments=24):
		self.segments = segments
		self.vertices = []

		if any(offset):
			raise NotImplementedError

		full_circle = 2 * pi
		arc_len = full_circle / self.segments

		for i in range(self.segments):
			arc = arc_len * i
			self.vertices.append([cos(arc) * scale, sin(arc * scale)])
			arc = arc_len * (i + 1)
			self.vertices.append([cos(arc) * scale, sin(arc) * scale])
			self.vertices.append([0.0, 0.0])

	@property
	def size(self):
		vert = self.vertices[0]
		diameter = sqrt(pow(vert[0], 2) + pow(vert[1], 2))
		return diameter, diameter

	def frame_vertices(self, thickness=0.25):
		scale = 1 - thickness
		verts = []

		inner = None
		for vert in self.vertices:
			if inner:
				verts.append(vert)
				verts.append(inner)
			verts.append(vert)
			inner = [vert[0] * scale, vert[1] * scale]
			verts.append(inner)

		return verts


class Sphere(BasicShape):
	def __init__(self, scale=1.0, offset=(0.0, 0.0, 0.0), segments=24, rings=12):
		self.segments = segments
		self.vertices = []

		full_circle = 2 * pi
		arc_len = full_circle / self.segments

		circle_verts = []
		for i in range(self.segments):
			arc = arc_len * i
			circle_verts.append([cos(arc), sin(arc), 0.0])
			arc = arc_len * (i + 1)
			circle_verts.append([cos(arc), sin(arc), 0.0])
			circle_verts.append([0.0, 0.0, 0.0])

		upper = None

		# TODO: better way of drawing a sphere
		prev_height = 0
		next_height = 0
		prev_scale = scale
		for _ in range(int(rings/2)):
			next_height += 2 / rings
			next_scale = sqrt(1 - next_height ** 2) * scale
			for circle_vert in circle_verts:
				if upper:
					self.vertices.append([circle_vert[0] * prev_scale, circle_vert[1] * prev_scale, prev_height * scale])
					self.vertices.append(upper)

				self.vertices.append([circle_vert[0] * prev_scale, circle_vert[1] * prev_scale, prev_height * scale])
				upper = [circle_vert[0] * next_scale, circle_vert[1] * next_scale, next_height * scale]
				self.vertices.append(upper)
			prev_height = next_height
			prev_scale = next_scale

		prev_height = 0
		next_height = 0
		prev_scale = scale
		for _ in range(int(rings / 2)):
			next_height -= 2 / rings
			next_scale = sqrt(1 - next_height ** 2) * scale
			for circle_vert in circle_verts:
				if upper:
					self.vertices.append([circle_vert[0] * prev_scale, circle_vert[1] * prev_scale, prev_height * scale])
					self.vertices.append(upper)

				self.vertices.append([circle_vert[0] * prev_scale, circle_vert[1] * prev_scale, prev_height * scale])
				upper = [circle_vert[0] * next_scale, circle_vert[1] * next_scale, next_height * scale]
				self.vertices.append(upper)
			prev_height = next_height
			prev_scale = next_scale

		self.offset(offset)

	def offset(self, offset):
		for i, vert in enumerate(self.vertices):
			self.vertices[i] = deepcopy(vert)
			for j, offs in enumerate(offset):
				self.vertices[i][j] += offs

	@property
	def size(self):
		vert = self.vertices[0]
		diameter = sqrt(pow(vert[0], 2) + pow(vert[1], 2))
		return diameter, diameter

	def frame_vertices(self, thickness=0.25):
		scale = 1 - thickness
		verts = []

		inner = None
		for vert in self.vertices:
			if inner:
				verts.append(vert)
				verts.append(inner)
			verts.append(vert)
			inner = [vert[0] * scale, vert[1] * scale]
			verts.append(inner)

		return verts

class MeshShape3D(BasicShape):

	def __init__(self, mesh, fix_zfighting=True, vertex_groups=None, weight_threshold=0.2):
		self._indices = []
		self.fix_zfighting = fix_zfighting
		self.tris_from_mesh(mesh, vertex_groups=vertex_groups, weight_threshold=weight_threshold)

	def get_vertices(self, eval_mesh):
		"""Return positions of the vertices of the already stored indicies."""

		if not self.fix_zfighting:
			return [eval_mesh.vertices[i].co for i in self._indices]

		verts = [eval_mesh.vertices[i].co for i in self._indices]
		verts = np.array([eval_mesh.vertices[i].co for i in self._indices], 'f')

		# Unfortunately this scaling has a massive performance impact.
		average = np.average(verts, axis=0)
		verts -= average
		verts *= 1.001
		verts += average

		return verts

	def tris_from_mesh(self, obj, vertex_groups=[], weight_threshold=0.2):
		depsgraph = bpy.context.evaluated_depsgraph_get()
		eval_ob = obj.evaluated_get(depsgraph)
		mesh = eval_ob.data
		mesh.calc_loop_triangles()

		self._indices = []
		if vertex_groups:
			group_idx = [obj.vertex_groups[vertex_group].index for vertex_group in vertex_groups]

			for tris in mesh.loop_triangles:
				if all(any(g.weight > weight_threshold for g in mesh.vertices[i].groups if g.group in group_idx) for i in tris.vertices):
					self._indices.extend(tris.vertices)
		else:
			indices = np.empty((len(mesh.loop_triangles), 3), 'i')
			mesh.loop_triangles.foreach_get(
				"vertices", np.reshape(indices, len(mesh.loop_triangles) * 3))

			self._indices = np.concatenate(indices)


class MeshShape2D(BasicShape):
	def __init__(self, mesh, scale=1.0):
		super().__init__(scale)
		self.tris_from_mesh(mesh, scale=scale)

	def tris_from_mesh(self, mesh, scale=100, matrix=None, view_axis=Axis.Y):
		mesh.calc_loop_triangles()

		vertices = np.empty((len(mesh.vertices), 3), 'f')
		indices = np.empty((len(mesh.loop_triangles), 3), 'i')

		mesh.vertices.foreach_get(
			"co", np.reshape(vertices, len(mesh.vertices) * 3))
		mesh.loop_triangles.foreach_get(
			"vertices", np.reshape(indices, len(mesh.loop_triangles) * 3))

		if matrix:
			# we invert the matrix as we are facing the object
			np_mat = np.array(matrix.normalized().inverted().to_3x3())
			vertices *= matrix.to_scale()
			np.copyto(vertices, vertices @ np_mat)
			vertices += matrix.translation

		# remove view axis
		vertices = np.delete(vertices, view_axis.value, 1)
		# scale
		vertices *= scale

		self.vertices = [vertices[i] for i in np.concatenate(indices)]
