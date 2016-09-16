#!/usr/bin/python3
# -*- coding: utf-8 -*-

import kivy
from kivy.graphics import *
from kivy.graphics import Color, Ellipse
from kivy.graphics.transformation import Matrix
from kivy.graphics.opengl import *
from kivy.resources import resource_find

kivy.require('1.9.1') # replace with your current kivy version !

import sys

import numpy as np

from colored_output import BColors as BC
printe = BC.printe
printw = BC.printw
printi = BC.printi
printok = BC.printok

class ModelLoader( object ):
    """ Class Description

    Parses an OBJ file. 
    """

    def __init__( self, srcs, **kwargs ):
        self._currentModel = None

        self.models = {}
        self.vertices = []
        self.normals = []
        self.texcoords = []
        self.faces = []

        self.counter = 0

        try:
            for src in srcs:
                self.loadModel( src )

                printi( "File processed:", src[0], "\n" )

        except:
            printe( "Model not found:", src[0] )
            print("Unexpected error:", sys.exc_info() )
            sys.exit(1)

    def loadModel( self, src ):
        """ Method Description

        Parses the OBJ file containing model data. Uses the parseOBJFaceData method to extract face information.

        WARNING: Comments correspond to triangulates mesh information.
        """

        objSrc      = resource_find( src[0] )
        shaderSrc   = resource_find( src[1] )

        with open( objSrc, 'r' ) as f:
            for l in f:

                if l.startswith('#'):
                    continue
                if l.startswith('s'):
                    continue

                l = l.rstrip()
                d = l.split( " " )

                if not d:
                    continue
                elif "o" == d[0]:
                    self.finishObject( objSrc, shaderSrc )
                    printi( "Constructing", d[1], "(glmodel.py)" )
                    self._currentModel = d[1]
                elif "v" == d[0]: # v vx vy vz
                    v = list( map( float, d[1:4] ) )
                    self.vertices.append( v )
                elif "vt" == d[0]: # vt u v
                    vt = list( map( float, d[1:3] ) )
                    self.texcoords.append( vt )
                elif "vn" == d[0]: # vn nx ny nz
                    vn = list( map( float, d[1:4] ) )
                    self.normals.append( vn )
                elif "f" == d[0]:       # f v/vt/vn
                    faceIndices = []    # [v1, v2, v3]
                    textureIndices = [] # [vt1, vt2]
                    normalsIndices = [] # [vn1, vn2, vn3]

                    for v in d[1:]:
                        w = v.split( '/' )
                        faceIndices.append( int( w[0] ) )

                        if len( w ) >= 2 and len( w[1] ) > 0:
                            textureIndices.append( int( w[1] ) )
                        else:
                            textureIndices.append( -1 )

                        if len( w ) >= 3 and len( w[2] ) > 0:
                            normalsIndices.append( int( w[2] ) )
                        else:
                            normalsIndices.append( -1 )

                    # Appends the touple: ( [v1, v2, v3], [vt1, vt2], [vn1, vn2, vn3] )
                    self.faces.append( ( faceIndices, textureIndices, normalsIndices ) )

            self.finishObject( objSrc, shaderSrc ) # Construct last Model

    def finishObject( self, objSrc, shaderSrc ):
        # If this is the first orject read, wait untill its data has been parsed
        if self._currentModel is None:
            return

        self.counter += 1

        model = Model( name = self._currentModel, src = objSrc, shader = shaderSrc )
        idx = 0
        for f in self.faces:
            """ Method Description

            WARNING: Comments correspond to triangulates mesh information.

            self.faces is n array of face touples:
                self.faces = [
                    ( [v1, v2, v3], [vt1, vt2], [vn1, vn2, vn3] ),
                    ( [v1, v2, v3], [vt1, vt2], [vn1, vn2, vn3] ),
                    ...
                ]

            therefore, f is a single touple:
                ( [v1, v2, v3], [vt1, vt2], [vn1, vn2, vn3] )

            Indeces in an OBJ file start from 1 not 0, therefore a correction (-1) is needed when accessing the vertex information from the corresponding arrays.
            """

            verts   = f[0] # [v1, v2, v3]
            tcs     = f[1] # [vt1, vt2]
            norms   = f[2] # [vn1, vn2, vn3]
            for i in range(3):
                # Get vertex components
                v = self.vertices[verts[i] - 1]     # v = [x, y, z]

                # Get texture coordinate components
                t = ( 0.0, 0.0 )
                if tcs[i] != -1:
                    t = self.texcoords[tcs[i] - 1]  # t = [u, v]

                # Get normal components
                n = ( 0.0, 0.0, 0.0 )
                if norms[i] != -1:
                    n = self.normals[norms[i] - 1]  # n = [x, y, z]

                data = [v[0], v[1], v[2], t[0], t[1], n[0], n[1], n[2]]
                model.vertices.extend( data )

            tri = [idx, idx + 1, idx + 2]
            model.indices.extend( tri )
            idx += 3

        self.models[self._currentModel] = model

        # print( " ---- " +
        #     self._currentModel +
        #     " (" + str( self.counter ) +
        #     ") ----",
        #     "\n  verticis:", model.vertices,
        #     "\n  indices:", model.indices, "\n" )

        self._currentModel = None
        self.vertices = []
        self.normals = []
        self.texcoords = []
        self.faces = []

    def getModels( self ):
        return list( self.models.values() )

class Model( object ):

    def __init__( self, **kwargs ):
        self.name = resource_find( kwargs.get( "name", None ) )
        self.src = resource_find( kwargs.get( "src", None ) )
        self.shader = resource_find( kwargs.get( "shader", "shaders/silple.glsl" ) )

        self.vFormat = kwargs.get( "vFormat",
            [
                ( b'v_pos', 3, 'float' ),
                ( b'v_tc0', 2, 'float' ),
                ( b'v_normal', 3, 'float' )
            ]
        )

        # Positions are in World Coordinates
        self.vertices = []
        self.indices = []

        self.rotAngle = 0
        self.rotAxis = ( 0, 1, 0 )

        self.position = { "x": 0, "y": 0, "z": 0 }

        self.rMatrix = Matrix()
        self.tMatrix = Matrix()
        self.mMatrix = Matrix()
        self.nMatrix = Matrix()

        self.applyTransform()

    def calculateNormals(self):
        for i in range(len(self.indices) / (3)):
            fi = i * 3
            v1i = self.indices[fi]
            v2i = self.indices[fi + 1]
            v3i = self.indices[fi + 2]

            vs = self.vertices
            p1 = [vs[v1i + c] for c in range(3)]
            p2 = [vs[v2i + c] for c in range(3)]
            p3 = [vs[v3i + c] for c in range(3)]

            u, v = [0, 0, 0], [0, 0, 0]
            for j in range(3):
                v[j] = p2[j] - p1[j]
                u[j] = p3[j] - p1[j]

            n = [0, 0, 0]
            n[0] = u[1] * v[2] - u[2] * v[1]
            n[1] = u[2] * v[0] - u[0] * v[2]
            n[2] = u[0] * v[1] - u[1] * v[0]

            for k in range(3):
                self.vertices[v1i + 3 + k] = n[k]
                self.vertices[v2i + 3 + k] = n[k]
                self.vertices[v3i + 3 + k] = n[k]

    def addRotation( self, a ):
        """ Method Description

        Increase rotation angle (rotAngle) by a
        """
        self.rotAngle += np.radians( a )
        self.rMatrix.rotate( np.radians( a ), *self.rotAxis )

    def setRotation( self, a, x, y, z ):
        """ Method Description

        Rotation object by angle a around the vector (x, y, z). Sets rotAngle to a, and rotAxis to (x, y, z)
        """
        if self.rotAngle != np.radians( a ) or self.rotAxis[0] != x or self.rotAxis[1] != y or self.rotAxis[2] != z:
            self.rotAngle   = np.radians( a )
            self.rotAxis    = ( x, y, z )
            self.rMatrix.identity().rotate( self.rotAngle, x, y, z )

    def addTranslation( self, x, y, z ):
        """ Method Description

        Add the vecor (x, y, z) to the current position vector.
        """

        self.position["x"] = x
        self.position["y"] = y
        self.position["z"] = z
        self.tMatrix.translate( x, y, z )

    def setTranslation( self, x, y, z ):
        """ Method Description

        Move to position (x, y, z). Equivalently, replace the position vector by (x, y, z)
        """

        if x != self.position["x"] or y != self.position["y"] or z != self.position["z"]:
            self.position["x"] = x
            self.position["y"] = y
            self.position["z"] = z
            self.tMatrix.identity().translate( x, y, z )

    def applyTransform( self ):
        offset = 0
        length = 0
        entryLength = 0

        flag = True
        for e in self.vFormat:
            entryLength += e[1]
            if b"pos" in e[0]:
                length = e[1]
                flag = False
            elif flag:
                offset += entryLength

    def setup( self ):
        """ Method Description

        Loads the model and transformation data to the Kivy OpenGL implementation.

        The proper order to apply matrices is:
            mMatrix     = tMatrix.multiply( rMatrix )
            mvMatrix    = vMatrix.multiply( mMatrix )

            where:
              - rMatrix: is the rotation matrix (to be applied first)
              - tMatrix: is the translation matrix (to be applied second)
              - mMatrix: is the model matrix
              - vMatrix: is the view matrix (to be applied third)

        When drawing a mesh 4 parameters have to be provided:
         - vertice, which should be added to a single array:
            vertices = [x1, y1, z1, u1, v1, x2, y2, z2, u2, v2, ...]
                        +------ i1 ------+  +------ i2 ------+

            Where ( x, y, z ) are position coordinates, while ( u, v ) are textel coordinates. Colors in the form of ( r, g, b ) can be provided instead of texel coordinates.

         - mode, as one of the following:
            ‘points’, ‘line_strip’, ‘line_loop’, ‘lines’, ‘triangles’, ‘triangle_strip’ or ‘triangle_fan’

            Unlike OpenGL, OpenGL ES - and the implementation supported by Kivy - does not allow rendering with quads.

         - indeces, should be added to a single array:
            indeces = [i1, i2, i3, ...]

            In OpenGL ES 2.0 and in Kivy's graphics implementation, we cannot have more than 65535 indices.

         - fmt, should be an array of format touples:
            (variable_name as byte, size, type)
            e.g. if the shader source contains the attributes vec3 v_pos and vec4 v_color, then they can be accessed as:
                vertex_format = [
                    (b'v_pos', 3, 'float'),
                    (b'v_color', 4, 'float'),
                ]

        To load a matrix to the OpenGL shader, one must add the matrix to the RenderContext as follows:

            renderContext['matrix_name'] = myMatrix
        """

        Color(0, 0, 0, 1)

        UpdateNormalMatrix()

        # XXX With the following 'with' statement, the mesh is bound to the renderContext. This binding is crucial, as the Mesh object has the facilities to look for any changes in the renderContext - through the global variable the 'with' statement sets -, and to react to it by redrawing the canvas. (see 'update' method)
        with self.renderContext:
            self.mesh = Mesh(
                vertices = self.vertices,
                indices = self.indices,
                fmt = self.vFormat,
                mode = 'triangles',
            )

    def getMvMatrix( self, vMatrix ):
        return vMatrix.multiply( self.mMatrix )

    def getNormMatrix( self, vMatrix ):
        return vMatrix.multiply( self.mMatrix ).normal_matrix()

    def setup( self ):
        """ Method Description

        Loads the model and transformation data to the Kivy OpenGL implementation.

        The proper order to apply matrices is:
            mMatrix     = tMatrix.multiply( rMatrix )
            mvMatrix    = vMatrix.multiply( mMatrix )

            where:
              - rMatrix: is the rotation matrix (to be applied first)
              - tMatrix: is the translation matrix (to be applied second)
              - mMatrix: is the model matrix
              - vMatrix: is the view matrix (to be applied third)

        When drawing a mesh 4 parameters have to be provided:
         - vertice, which should be added to a single array:
            vertices = [x1, y1, z1, u1, v1, x2, y2, z2, u2, v2, ...]
                        +------ i1 ------+  +------ i2 ------+

            Where ( x, y, z ) are position coordinates, while ( u, v ) are textel coordinates. Colors in the form of ( r, g, b ) can be provided instead of texel coordinates.

         - mode, as one of the following:
            ‘points’, ‘line_strip’, ‘line_loop’, ‘lines’, ‘triangles’, ‘triangle_strip’ or ‘triangle_fan’

            Unlike OpenGL, OpenGL ES - and the implementation supported by Kivy - does not allow rendering with quads.

         - Indices, should be added to a single array:
            Indices = [i1, i2, i3, ...]

            In OpenGL ES 2.0 and in Kivy's graphics implementation, we cannot have more than 65535 indices.

         - fmt, should be an array of format touples:
            (variable_name as byte, size, type)
            e.g. if the shader source contains the attributes vec3 v_pos and vec4 v_color, then they can be accessed as:
                vertex_format = [
                    (b'v_pos', 3, 'float'),
                    (b'v_color', 4, 'float'),
                ]

        To load a matrix to the OpenGL shader, one must add the matrix to the RenderContext as follows:

            renderContext['matrix_name'] = myMatrix
        """
        pass

    def update( self, **kwargs ):
        """ Method Description
        Calculate the model matrix (mMatrix)

        In kivy, m1.multiply( m2 ) means: m2.m1 where . is the matrix product operator.
        """

        self.mMatrix = self.tMatrix.multiply( self.rMatrix )
