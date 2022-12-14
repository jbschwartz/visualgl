import ctypes
import struct

from .stl_type import STLType


class STLWriter:
    FILE_EXTENSION = ".stl"

    def __init__(self, file_name, file_type: STLType = STLType.BINARY):
        if file_name[-4:] != self.FILE_EXTENSION:
            file_name += self.FILE_EXTENSION

        self.file_name = file_name
        self.file_type = file_type

    def write(self, meshes):
        with open(self.file_name, self.file_type.write_mode()) as file:
            file.write(self.header())
            # Placeholder bytes for number of facets
            file.write(bytes(4))

            num_facets = 0
            mesh_id = 0
            for mesh in meshes:
                for facet in mesh.facets:
                    normal = facet.normal if facet.normal is not None else facet.computed_normal
                    buffer = [
                        *normal,
                        *facet.vertices[0],
                        *facet.vertices[1],
                        *facet.vertices[2],
                        mesh_id,
                    ]
                    file.write(struct.pack("<fff fff fff fff H", *buffer))
                    num_facets += 1

                mesh_id += 1

            # Go back to the beginning to write the number of facets
            file.seek(80)
            file.write(bytes(ctypes.c_uint32(num_facets)))

    def header(self):
        # Header is 80 bytes long
        header = "Written by robotpy, http://www.github.com/jbschwartz/robotpy"
        return header.encode() + bytes(80 - len(header))
