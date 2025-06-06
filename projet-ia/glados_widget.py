#!/usr/bin/env python3
from PyQt6.QtWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QTimer
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np

class GLaDOSWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        print("Initializing GLaDOS widget...")
        self.setMinimumSize(300, 300)
        
        # Animation timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(16)  # ~60 FPS
        
        # Rotation angle
        self.rotation = 0.0
        
    def initializeGL(self):
        print("Initializing OpenGL...")
        try:
            glClearColor(0.0, 0.0, 0.0, 1.0)
            glEnable(GL_DEPTH_TEST)
            glEnable(GL_LIGHTING)
            glEnable(GL_LIGHT0)
            glEnable(GL_COLOR_MATERIAL)
            
            # Set up light
            glLightfv(GL_LIGHT0, GL_POSITION, (0, 0, 10, 1))
            glLightfv(GL_LIGHT0, GL_AMBIENT, (0.2, 0.2, 0.2, 1))
            glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.8, 0.8, 0.8, 1))
            print("OpenGL initialization successful")
        except Exception as e:
            print(f"Error in initializeGL: {str(e)}")
            raise
        
    def resizeGL(self, width, height):
        print(f"Resizing OpenGL viewport to {width}x{height}")
        try:
            glViewport(0, 0, width, height)
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            gluPerspective(45, width / height, 0.1, 100.0)
            glMatrixMode(GL_MODELVIEW)
        except Exception as e:
            print(f"Error in resizeGL: {str(e)}")
            raise
        
    def paintGL(self):
        try:
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glLoadIdentity()
            
            # Position the camera
            gluLookAt(0, 0, 5, 0, 0, 0, 0, 1, 0)
            
            # Rotate the model
            glRotatef(self.rotation, 0, 1, 0)
            self.rotation += 0.5
            
            # Draw a simplified GLaDOS-like shape
            self.draw_glados()
        except Exception as e:
            print(f"Error in paintGL: {str(e)}")
            raise
        
    def draw_glados(self):
        try:
            # Main body (sphere)
            glColor3f(0.7, 0.7, 0.7)
            sphere = gluNewQuadric()
            gluSphere(sphere, 1.0, 32, 32)
            
            # Eye (smaller sphere)
            glPushMatrix()
            glTranslatef(0.3, 0.2, 0.8)
            glColor3f(0.9, 0.1, 0.1)  # Red eye
            gluSphere(sphere, 0.2, 16, 16)
            glPopMatrix()
            
            # Arms (cylinders)
            glColor3f(0.6, 0.6, 0.6)
            for angle in [45, -45]:
                glPushMatrix()
                glRotatef(angle, 0, 1, 0)
                glTranslatef(0, 0, 1.5)
                glRotatef(90, 1, 0, 0)
                gluCylinder(sphere, 0.1, 0.1, 1.0, 16, 1)
                glPopMatrix()
                
            gluDeleteQuadric(sphere)
        except Exception as e:
            print(f"Error in draw_glados: {str(e)}")
            raise 