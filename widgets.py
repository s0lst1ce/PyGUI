import pygame as pg
from pygame import freetype
from collections import namedtuple
from colors import *
from events import *
import os

Offset = namedtuple("Offset", ["x", "y"])

class Widget(object):
	"""An abstract class from which most widgets inherit. Must always belong to a Container.
	w:     width of the widget
	h:     height of the widget
	surf:  surface to pass to the widget. This will be overriden if special methods build their own surfaces
	img:   image file to be laoded from disk. This argument must be a tuple of strings specifying the relative path to the asset.
	alpha: whether the widget must provide support for the alpha channel. If True the given surface (if any) will be converted to alpha. Likewise it will be converted to RGB profile otherwise for improved performance.

	If both surf and img arguments are provided then the class will give an error upon creation."""
	def __init__(self, w, h, surf=None, img=None, alpha=True):
		self.w = w
		self.h = h
		self.hovered = False

		#making surface
		assert surf==None or img==None, ValueError(f"Both surf ({surf}) and img ({img}) were provided.")
		if surf:
			self.surf = surf
		elif img:
			self.surf = self.load_img(img)

		self.changed = True #whether the surface has changed since the last time the container read it.


	def load_img(self, path):
		"""return a surface representing the image located at the specified "path" location. The surface will be of the appropriate profile (RGB or RGBA)"""
		surf = pg.image.load(os.path.join(*path))

		if self.alpha:
			return surf.convert_alpha()
		else:
			return surf.convert()


	def update(self, *args):
		"""generic update function. All widgets should have one since containers will expect one."""
		pass


class Label(Widget):
	"""Label is a class which provides methods for some common actions used by classes which render text.
	See Widget for the 4 first arguments.

	text:       string representing the text to be rendered
	bccolor:    background color
	fgcolor:    color of the text
	font:       font to be used. None will default to Pygame's default font
	underlined: whether the text should be underlined. This is a software rendering post-processing.
	bold:       whether the text should be bold. Note that this is a software rendering post-processing done on the font. Prefer bold fonts instead
	background: a surface or path to image to be used as background. Path may be a string or tuple of strings"""
	def __init__(self, w, h, *args, alpha=False, text="", bgcolor=None, fgcolor=BLACK, font=None, font_size=20, underlined=False, bold=False, background=None, **kwargs):
		super(Label, self).__init__(w, h, alpha=alpha)
		#making sure arguments are valid
		if bgcolor==None:
			if background==None:
				if alpha==None:
					raise TypeError(f"A background, bgcolor, or alpha must be set")
		else:
			if background:
				raise ValueError(f"Can't set background and bgcolor")

		#text properties
		self._text = text
		self.fgcolor = fgcolor
		self.bold = bold
		self.underlined = underlined

		#font
		self.font = freetype.Font(font, font_size) #None means pg default
		self.font.underline = underlined
		self.font.strong = bold
		self.font.fgcolor = self.fgcolor

		#surface
		if background:
			if isinstance(background, pg.Surface):
				surf = background
			elif isinstance(background, tuple):
				surf = pg.image.load(os.path.join(*background)).convert()
			elif isinstance(background, str):
				surf = pg.image.load(background).convert()
			self.bgsurf = pg.transform.scale(surf, (w, h))
		else:
			if bgcolor:
				self.bgcolor = bgcolor
			else:
				if alpha:
					self.bgcolor = ALPHA
				else:
					self.bgcolor = WHITE

			self.bgsurf = pg.Surface((w, h))
			self.bgsurf.fill(self.bgcolor)
		self.surf = self.bgsurf.copy()


		#rendering text TODO: implement font scaling to fit text into provided surface
		nrect = self.font.get_rect(self._text)
		if nrect.w>self.w or nrect.h>self.h:
			raise ValueError("Text size larger than widget")
		self.make_surf()

	def __repr__(self):
		return f'''<Label({self.w}, {self.h}), text="{self._text}"'''

	@classmethod
	def from_background(cls, background, *args, **kwargs):
		if isinstance(background, pg.Surface):
			surf = background
		elif isinstance(background, tuple):
			surf = pg.image.load(os.path.join(*background)).convert()
		elif isinstance(background, str):
			surf = pg.image.load(background).convert()
		else:
			raise TypeError(f"background must be a tuple of strings representing a path to an image or a Pygame Surface not {background}")

		rect = surf.get_rect()
		return cls(rect.w, rect.h, *args, background=background, **kwargs)


	@property
	def text(self):
		return self._text

	@text.setter
	def text(self, string):
		nrect = self.font.get_rect(string)
		if nrect.w>self.w or nrect.h>self.h:
			raise ValueError("Text size larger than widget")
		self.changed = True
		previous_text = self._text
		self._text = string
		self.make_surf(old_text=previous_text)

	def render_text(self):
		if not self.changed:
			return self.txt_surf

		return self.font.render(self._text) #save the given Rect for make_surf instead of recalculating it


	def make_surf(self, old_text=None):
		if not self.changed:
			return

		#blitting background surface back on the main surface. -> fixes overlapping characters
		if not old_text:
			self.surf.blit(self.bgsurf, (0, 0))
		else:
			subrect = self.font.get_rect(old_text)
			offset = self.text_offsets(text=old_text)
			self.surf.blit(self.bgsurf, (offset.x, offset.y), area=subrect)

		offset = self.text_offsets(text=self._text)
		self.surf.blit(self.render_text()[0], (offset.x, offset.y))

	def text_offsets(self, text=""):
		rect = self.font.get_rect(text)
		x_offset = (self.w-rect.w)/2
		y_offset = (self.h-rect.h)/2
		return(Offset(x_offset, y_offset))

class AbstractButton(Widget):
	"""docstring for Button"""
	def __init__(self, w, h, *args, alpha=False, action=None, **kwargs):
		super().__init__(w, h, alpha=alpha)
		self.w = w
		self.h = h
		self.action = action
		self.events = [pg.MOUSEBUTTONUP]

	def update(self):
		super(AbstractButton, self).update()
		if self.hovered:
			global PYGUI_DISPATCHER
			events = PYGUI_DISPATCHER[self]
			if events:
				self.action()


class TextButton(AbstractButton, Label):
	"""a button with text"""
	def __init__(self, w, h, alpha=False, action=None, text="", bgcolor=None, fgcolor=BLACK, font=None, font_size=20, underlined=False, bold=False, max_chars=False):
		super().__init__(w, h, alpha=False, action=action, text=text, bgcolor=None, fgcolor=BLACK, font=None, font_size=20, underlined=False, bold=False, max_chars=False)



'''NEEDED WIDGETS LIST
- Label
- Input
- Buttons
	- ImageButton
	- TextButton

Container:
A container holds multiple widgets into itself. It can be thought of as a "box" containing other widgets.
They can sometimes be seen as menus as well although they are more abstract than them. Those can be organized in different ways.
- Tabs
- Menus
- Container


'''