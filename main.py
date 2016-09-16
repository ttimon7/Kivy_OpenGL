#!/usr/bin/python3
# -*- coding: utf-8 -*-

import kivy
from kivy.app import App
from kivy.config import Config
from kivy.graphics import *
from kivy.graphics import Color, Ellipse
from kivy.graphics.transformation import Matrix
from kivy.graphics.opengl import *
from kivy.resources import resource_find
from kivy.lang import Builder
from kivy.properties import ObjectProperty, ListProperty
from kivy.core.window import Window
from kivy.clock import Clock

from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.actionbar import ActionButton, ActionGroup
from kivy.uix.popup import Popup

from kivy.uix.scrollview import ScrollView

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout

kivy.require('1.9.1') # replace with your current kivy version !

import sys, os, random, json
import pygame

import numpy as np
from numpy import array

from colored_output import BColors as BC
printe = BC.printe
printw = BC.printw
printi = BC.printi
printok = BC.printok

from glmodel import *

class OpenGLWidgetRC( Widget ):
    """ Class Description

    Attempts to render multiple 3D models using RenderContexts, where each 3D model has its own shader stored in the associated RenderContext.

    ---- FIXME -----------------------------------------------------------------

        The shaders stored in the models RenderContexts are applied
        correctly - at least I think, since the transformations, evoked by
        the application of the rotation and translation matrices take place
        correctly, and effect only the models they should -, but then,

    ----------------------------------------------------------------------------
    """
    opengl_widget = ObjectProperty( None )

    def __init__( self, **kwargs ): # Normal constructor method

        # Creating a storage for the RenderContexts associated with the 3D models
        self.instructions = InstructionGroup()

        # Preparing canvas for storing instructions and the shader
        self.canvas = RenderContext()
        self.canvas.shader.source = "shaders/simple.glsl" # FIXME something goes wrong here, maybe

        self.rcs = []
        self.rots = []
        self.trans = []
        self.meshes = []

        self.counter = 0

        self.pMatrix = Matrix()
        self.vMatrix = Matrix()

        Window.bind( on_keyboard = self.keyboard_handler )

        super( OpenGLWidgetRC, self ).__init__( **kwargs )

    def init( self, **kwargs ):
        # Loading models
        self.models = kwargs.get( "models", [] )

        # Creating instruction spaces for the models
        for i in range( len( self.models ) ):
            m = self.models[i]
            self.rcs.append( RenderContext( compute_normal_mat = True ) )
            self.rcs[i].shader.source = m.shader

            self.instructions.add( self.rcs[i] )

        # Initializing projection and view matrices
        aspect = self.width / float( self.height )
        self.pMatrix.perspective( 45.0, aspect, 1.0, 80.0 )
        self.vMatrix = Matrix().look_at(
            0.0, 0.0, 15.0, # Eye coordinates x, y, z
            0.0, 0.0, 0.0, # Reference point x, y, z (Eye and the up vector are given relative to this)
            0.0, 1.0, 0.0) # Up vector x, y, z

        self.canvas.add( self.instructions )
        with self.canvas:
            self.cb = Callback( self.setup_gl_context )
            PushMatrix()
            self.setup_scene_with_rcs()
            PopMatrix()
            self.cb = Callback( self.reset_gl_context )

        Clock.schedule_once( self.update_glsl, 1 / 40. )

    def setup_gl_context(self, *args):
        glEnable(GL_DEPTH_TEST)

    def reset_gl_context(self, *args):
        glDisable(GL_DEPTH_TEST)

    def update_glsl(self, *args):
        self.counter += 1

        aspect = self.width / float(self.height)
        self.pMatrix = Matrix().view_clip( -aspect, aspect, -1, 1, 1, 100, 1 )

        for i in range( len( self.models ) ):

            PushMatrix()

            m = self.models[i]

            m.addRotation( 1 )

            if i == 0:
                m.setTranslation( -1, 3, 0 )

            elif i == 1:
                m.setTranslation( -1, -3, 0 )

            m.update()

            self.rcs[i]['projection_mat'] = self.pMatrix
            self.rcs[i]['modelview_mat'] = m.getMvMatrix( self.vMatrix )

            PopMatrix()

        Clock.schedule_once( self.update_glsl, 1 / 40. )

    def setup_scene_with_rcs( self ):
        Color( 0, 0, 0, 1 )

        for i in range( len( self.models ) ):
            m = self.models[i]

            with self.rcs[i]:
                Color( 0, 0, 0, 1 )
                PushMatrix()

                """
                If the fragment shader has a "uniform mat4 normal_mat" property, the UpdateNormalMatrix() will update it.
                """
                UpdateNormalMatrix()
                self.meshes.append(
                    Mesh(
                        vertices = m.vertices,
                        indices = m.indices,
                        fmt = m.vFormat,
                        mode = 'triangles',
                    )
                )

                PopMatrix()

    def keyboard_handler( self, key, asciiCode, code, text, *args, **kwargs ):
        """ Method Description

        Changes viewer position by updating the view matrix
        """

        offsetX = 0.
        offsetZ = 0.
        if asciiCode == 119 or asciiCode == 273: # w or up
            offsetZ += 0.5
        if asciiCode == 97 or asciiCode == 276: # a or left
            offsetX -= 0.5
        if asciiCode == 115 or asciiCode == 274: # s or down
            offsetZ -= 0.5
        if asciiCode == 100 or asciiCode == 275: # d or right
            offsetX += 0.5

        self.vMatrix.translate( offsetX, 0., offsetZ )

class OpenGLWidget( Widget ):
    """
    Renders multiple 3D models while relying on the single RenderContext of its canvas.

    ---- FIXME -----------------------------------------------------------------

        This renders the models **almost** as it should. The shader loaded
        to self.canvas is applyied correctly, but changing the shader on
        the fly does not seem to work, therfore the correction to the model
        matrix effects all the models displayed unifirmly.

    ----------------------------------------------------------------------------
    """

    opengl_widget = ObjectProperty( None )

    def __init__( self, **kwargs ): # Normal constructor method

        self.canvas = RenderContext( compute_normal_mat = True )
        printi( "Using canvas shader:", str( resource_find( 'shaders/simple.glsl' ) ) )
        self.canvas.shader.source = resource_find( 'shaders/simple.glsl' )

        self.pMatrix = Matrix()
        self.vMatrix = Matrix()

        # Registering keyboard event handler
        Window.bind( on_keyboard = self.keyboard_handler )

        super( OpenGLWidget, self ).__init__( **kwargs )

    def init( self, **kwargs ):
        # Loading models
        self.models = kwargs.get( "models", [] )

        # Initializing projection and view matrices
        aspect = self.width / float( self.height )
        self.pMatrix.perspective( 45.0, aspect, 1.0, 80.0 )
        self.vMatrix = Matrix().look_at(
            0.0, 0.0, 20.0, # Eye coordinates x, y, z
            0.0, 0.0, 0.0, # Reference point x, y, z (Eye and the up vector are given relative to this)
            0.0, 1.0, 0.0) # Up vector x, y, z

        self.canvas['projection_mat'] = self.pMatrix
        self.canvas['modelview_mat'] = self.vMatrix

        with self.canvas:
            self.cb = Callback( self.setup_gl_context )
            PushMatrix()
            self.setup_scene()
            PopMatrix()
            self.cb = Callback( self.reset_gl_context )

        Clock.schedule_once( self.update_glsl, 1 / 40. )

    def setup_gl_context(self, *args):
        glEnable(GL_DEPTH_TEST)

    def reset_gl_context(self, *args):
        glDisable(GL_DEPTH_TEST)

    def update_glsl(self, *args):
        aspect = self.width / float(self.height)
        self.pMatrix = Matrix().view_clip( -aspect, aspect, -1, 1, 1, 100, 1 )

        for i in range( len( self.models ) ):
            PushMatrix()

            m = self.models[i]

            m.addRotation( 1 )
            if i == 0:
                m.setTranslation( 4.5, 3, 5 ) # FIXME gets overwritten
            elif i == 1:
                m.setTranslation( 4.5, 0, 5 ) # FIXME since this comes later, this overrides

            m.update()

            self.canvas['projection_mat'] = self.pMatrix
            self.canvas['modelview_mat'] = m.getMvMatrix( self.vMatrix )

            PopMatrix()

        Clock.schedule_once( self.update_glsl, 1 / 40. )

    def setup_scene(self):
        Color( 0, 0, 0, 1 )

        for m in self.models:
            """
            If the fragment shader has a "uniform mat4 normal_mat" property, the UpdateNormalMatrix() will update it.
            """

            PushMatrix()

            UpdateNormalMatrix()

            Mesh(
                vertices=m.vertices,
                indices=m.indices,
                fmt=m.vFormat,
                mode='triangles',
            )

            PopMatrix()

    def keyboard_handler( self, key, asciiCode, code, text, *args, **kwargs ):
        """ Method Description

        Changes viewer position by updating the view matrix
        """
        offsetX = 0.
        offsetZ = 0.
        if asciiCode == 119 or asciiCode == 273: # w or up
            offsetZ += 0.5
        if asciiCode == 97 or asciiCode == 276: # a or left
            offsetX -= 0.5
        if asciiCode == 115 or asciiCode == 274: # s or down
            offsetZ -= 0.5
        if asciiCode == 100 or asciiCode == 275: # d or right
            offsetX += 0.5

        self.vMatrix.translate( offsetX, 0., offsetZ )

class RootWidget( BoxLayout ):
    path                    = os.path.abspath( os.path.dirname( "." ) )

    menu                    = ObjectProperty( None )
    opengl_widget_rc        = ObjectProperty( None )
    opengl_widget           = ObjectProperty( None )

    def __init__( self, **kwargs ): # Normal constructor method
        super( RootWidget, self ).__init__( **kwargs )

    def init( self ): # Trick to perform initialization when I need it, not upon instantiation
        ml = ModelLoader( [( "models/suzanne.obj", "shaders/simple.glsl" ), ( "models/torus.obj", "shaders/simple_blue.glsl" )] )

        models = ml.getModels()
        printi( "Number of models retrieved: ", str( len( models ) ) )

        # XXX Widget relying on multiple RenderContexts added to an InstructionGroup passed to self.canvas.
        self.opengl_widget_rc.init( models = models )

        # XXX Widget relying on a single RenderContext (self.canvas = RenderContext())
        self.opengl_widget.init( models = models )

class MyApp( App ):

    path = os.path.abspath( os.path.dirname( "." ) )

    def build( self ):
        self.title = "Simple Movie Archive"
        self.icon = str( os.path.join( self.path, "icons", "icon.png" ) )

        # Setting the window's size
        self.width  = self.config.getint( 'graphics', 'width' )
        self.height = self.config.getint( 'graphics', 'height' )
        Window.size = ( self.width, self.height )

        self.root   = Builder.load_file( os.path.join( self.path, "kvs", "RootWidget.kv" ) )
        self.root.init()

        return self.root

    def build_config( self, config ): # If there is no config file, create one, with the following parameters
        config.setdefaults( 'graphics', {
            'width': '800',
            'height': '200'
        })


if __name__ == '__main__':
    MyApp().run()
