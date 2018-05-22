#!/usr/bin/env python
# -*- coding: utf_8 -*-
import sys, os, time, simplejson, pygame, struct
import logging as L
import xml.etree.ElementTree as ET
from collections import deque
from random import randint

"""
	- OPTIMIZE > preload-cache UI graphics
	- OPTIMIZE > sprite UI graphics
	- UI beautifying
		- topbar buttons mouse background hover
	- detect multiple joysticks, not only the first!
	- autodetect pads in calibration
	- allow keyboard input
	- antialiasing? > gfxdraw
	- poly animations (pop, color transitions...)
	- CREATIVE > circlic visualizers
	- Frame delayed smoothing?
	- OPTIMIZE https://stackoverflow.com/questions/6395923/any-way-to-speed-up-python-and-pygame
"""

# L.basicConfig(filename='events.log', format='%(asctime)s: %(message)s', filemode='w', level=L.DEBUG)	# production
L.basicConfig(filename='events.log', format='%(asctime)s: %(message)s', level=L.DEBUG) 	# development

# the working directory of this script
# pwd = str(os.path.dirname(os.path.realpath(__file__)))	# __file__ is not known after py2exe compilation
pwd = os.getcwd()
L.debug('pwd is [%s]', pwd)

###### CONFIG VARS ######
CONFIG_FILE_PATH = os.path.join(pwd,'config.json')
L.debug('CONFIG_FILE_PATH=[%s]', CONFIG_FILE_PATH)

SHAPES_DIRECTORY = os.path.join(pwd,'SHAPES')
L.debug('SHAPES_DIRECTORY=[%s]', SHAPES_DIRECTORY)

colors = {
	'ACC' : (64, 255, 0),
	'BRK': (255, 0, 0),
	'STEER' : (255, 116, 56),
	'BG' : (255, 255, 255) }
controls = {
	'PAD_INDEX': 0,
	'acc': 5,
	'brk': 2,
	'steer': 0 }
DEFAULT_COLORS = {
	'BLACK' : (0, 0, 0),
	'DARKGRAY' : (100, 100, 100),
	'GRAY' : (180, 180, 180),
	'LIGHTGRAY' : (200, 200, 200),
	'WHITE' : (255, 255, 255),

	'MAGENTA' : (255, 51, 204),

	'TOPBAR_BACKGROUND' : (240, 240, 240),
	'TOPBAR_BACKGROUND_HOVER' : (250, 250, 250),

	'ACC' : (64, 255, 0),
	'BRK': (255, 0, 0),
	'STEER' : (255, 116, 56),
	'BG' : (255, 255, 255) }
PRINT_DEBUGS_ON = False
DEADZONE_ON = False
GREY_PREPAINT = True
DEADZONE = 0.0
SMOOTHING = 0
ANTIALIASING = False
WW = 500	# canvas width
WH = 300	# canvas height
FRAME_SIZE_LIMIT=((320, 1920),(220, 1080))
SQR = 50
TOPBAR_BUTTONS = [
	{ "command": "VIZ_CYCLE_PREV", "path": "UI/ICON_LEFT.png" },
	{ "command": "PRINT_DEBUGS_ON", "path": "UI/ICON_DEBUG_ON.png" },
													# "ICON_DEBUG_OFF.png"
	{ "command": "CALIBRATION", "path": "UI/ICON_CALIBRATE.png" },
	{ "command": "GREY_PREPAINT", "path": "UI/ICON_PREPAINT_ON.png" },
													# "ICON_PREPAINT_OFF.png"
	# { "command": "ANTIALIASING", "path": "icon_topbar_aa.png" },
													# "ICON_ANTIALIASING_ON.png"
													# 	ICON_ANTIALIASING_OFF.png"
	{ "command": "DEADZONE", "path": "UI/ICON_DEADZONE.png"},
	{ "command": "CYCLE_COLORS_ACC", "path": "UI/ICON_COLOR_ACC.PNG" },
	{ "command": "CYCLE_COLORS_BRK", "path": "UI/ICON_COLOR_BRK.PNG" },
	{ "command": "CYCLE_COLORS_STEER", "path": "UI/ICON_COLOR_STEER.PNG" },
	{ "command": "CYCLE_COLORS_BG", "path": "UI/ICON_COLOR_BG.PNG" },
	{ "command": "VIZ_CYCLE_NEXT", "path": "UI/ICON_RIGHT.png" }]
TOPBAR_AREA_HOVERS = False	## initially set the topbar to be hidden
COO = None	# the current (scaled) coordinates
SHAPES = []
MAINTENANCE = 0

# pad control values
VALUE_STEER = 0
VALUE_ACC = 0
VALUE_BRK = 0

def shape():
	return SHAPES[0]["KEY"]
def load_shapes(d):
	# read the directory for svg files and save the paths to the SHAPES[] list
	path = os.path.abspath(d)
	if os.path.exists(path) and os.path.isdir(path):
		for pa in os.listdir(path):
			tmp = os.path.join(path, pa)
			if os.path.exists(tmp) and os.path.isfile(tmp) and str(tmp.upper()).endswith('.SVG'):
				# buffer all svg filenames to a SHAPES[]
				try:
					open_test = open(tmp)
				except PermissionError as pe:
					L.error("PermissionError > cannot open and read file in path [%s]", tmp)
				else:
					add = {
						"KEY": os.path.basename(tmp).upper().replace(".SVG",''),
						"PATH": os.path.abspath(tmp).lower()
					}
					L.debug("loaded shape [%s] [%s]", add['KEY'], add['PATH'])
					SHAPES.append(add)

	if len(SHAPES) > 0:
		SHAPES.sort()
		L.debug("sorted loaded shapes ")
		return False
	else:
		return True
def cycle_viz(target):
	global SHAPES
	global COO
	dq = deque(SHAPES)
	if target!=None:
		for x in range(0,len(SHAPES)):
			# rotating the list once to left of right
			if target == -1:
				dq.rotate(-1)
				SHAPES = list(dq)
				break
			elif target == 1:
				dq.rotate(1)
				SHAPES = list(dq)
				break

			# when target is a string > directly pointing to a viz key
			# then the list is cycled until the targeted key is on SHAPES[0]
			if type(target) is str:
				if shape() != target:
					dq.rotate(1)
					SHAPES = list(dq)
				
				if shape()==target:
					break
	
	# load & correct scale the vector paths
	COO = parse_svg(SHAPES[0]['PATH'], WW, WH)
	L.info("CURRENT VIZ = [%s]",shape())
def num(s):
	try:
		return int(s)
	except ValueError:
		return float(s)
def parse_svg(filepath, ww, wh):
	# return a touple list of absolute coordinates to paint pygame polys with
	ll = {}
	# http://www.w3schools.com/svg/svg_path.asp
	tree = ET.parse(filepath)

	boundingbox = tree.find(".")	# get the bounding box dimensions
	BW = num(boundingbox.get('width'))
	BH = num(boundingbox.get('height'))
	rel_W = float(WW)/float(BW)
	rel_H = float(WH)/float(BH)
	# print "BW=[%s], BH=[%s]" % ( str(BW), str(BH) )

	elements = tree.findall(".//{0}path".format("{http://www.w3.org/2000/svg}"))
	for a in elements:
		u = a.get('d').split()
		l = []
		lastCommand = ''
		for c in u:
			co = c.split(',')
			if len(co) == 2:
				if rel_W < rel_H:
					x = num( (float(float(co[0])/BW)*WW) )
					y = num( (float(co[1]))  *rel_W ) + ((float(WH)-float(BH*rel_W))/2)
				else:
					x = num(float(co[0])*rel_H) + ((float(WW)-float(BW*rel_H))/2)
					y = num(float(float(co[1])/BH)*WH)
				# print a.get('id') + " >> " + str(x) + " | " + str(y)
				l.append( (x, y) )
			else:
				lastCommand = co[0]
		ll[a.get("id")] = l
	ll["BW"] = BW
	ll["BH"] = BH
	return ll
def set_config():
	WRITETHIS = {
		'color_acc':colors["ACC"], 
		'color_brk':colors["BRK"], 
		'color_steer':colors["STEER"], 
		'color_bg':colors["BG"], 
		'deadzone':float(DEADZONE),
		'prepaint':int(GREY_PREPAINT),
		'antialias':int(ANTIALIASING),
		'PRINT_DEBUGS_ON':int(PRINT_DEBUGS_ON),
		'smoothing':int(SMOOTHING),
		'window_w':WW,
		'window_h':WH,
		'initial_screen':shape(),
		'controls': controls
		# 'ANTIALIASING_ENABLED':ANTIALIASING_ENABLED
	}
	L.debug('current configuration = %s',WRITETHIS)

	f = open(CONFIG_FILE_PATH, 'w')
	simplejson.dump(WRITETHIS, f)
	f.close()
	L.info('saved configuration to [%s]',CONFIG_FILE_PATH)
def load_png_dimensions(filepath):
	with open(os.path.abspath(filepath), 'rb') as f:
		data = f.read(24)
		if( (data[:8] == '\211PNG\r\n\032\n') and (data[12:16] == 'IHDR') ):
			# print "DEBUG: [%s] is a png" % filepath
			w, h = struct.unpack('>LL', data[16:24])
			width = int(w)
			height = int(h)
			return (width, height)
		else:
			raise Exception('[%s] is not a png image' % filepath)
def frame_resize(event):
	try:
		global WW
		global WH
		if event.w >= FRAME_SIZE_LIMIT[0][0] and event.w <= FRAME_SIZE_LIMIT[0][1]:
			WW = event.w
		if event.h >= FRAME_SIZE_LIMIT[1][0] and event.h <= FRAME_SIZE_LIMIT[1][1]:
			WH = event.h
		global screen
		screen = pygame.display.set_mode((WW, WH), pygame.RESIZABLE | pygame.DOUBLEBUF)
		L.info("frame resized to (%s,%s)",str(WW), str(WH))
	except Exception as e:
		L.error(e)

class PngClickArea:
	def __init__(self, screen, xpos, ypos, imgpath):
		dims = load_png_dimensions(imgpath)
		self.dims = dims
		self.x = xpos
		self.y = ypos
		self.screen = screen
		self.img = pygame.image.load(imgpath).convert_alpha()
		self.hovers = False
	def to_string(self):
		return "self.dims=[%s], self.x=[%s], self.y=[%s], self.hovers=[%s]" % ( str(self.dims), str(self.x), str(self.y), str(self.hovers) )
	def hover(self, bo):
		self.hovers = bo
	def draw(self, screen):
		# print "hovers = [%s]" % str(self.hovers)
		if self.hovers:
			pygame.draw.rect(screen, (240,240,240), pygame.Rect((self.x, self.y), self.dims) )
		screen.blit(self.img, pygame.Rect((self.x, self.y), self.dims) )
	def validate_position(self, event):
		# print self.to_string()
		if (event.pos[0] in range(self.x, self.x+self.dims[0]) ) and (event.pos[1] in range(self.y, self.y+self.dims[1])):
			return True
	def reinit(self, imgpath):
		dims = load_png_dimensions(imgpath)
		self.dims = dims
		self.img = pygame.image.load(imgpath).convert_alpha()
		self.hovers = False
class TextPrint:
	def __init__(self):
		self.reset()
		self.font = pygame.font.SysFont("Verdana",13)
	def screenprint(self, screen, textString):
		textBitmap = self.font.render(textString, True, (0,0,0))
		screen.blit(textBitmap, [self.x, self.y])
		# pygame.display.flip()
		self.y += self.line_height
	def screenprint_buf(self, screen, textString, posX, posY):
		self.x = int(posX)
		self.y = int(posY)
		textBitmap = self.font.render(textString, True, (0,0,0))
		screen.blit(textBitmap, [self.x, self.y])
		# pygame.display.flip()
	def reset(self):
		self.x = 10
		global SQR
		global TOPBAR_AREA_HOVERS
		if TOPBAR_AREA_HOVERS:
			self.y = 10+SQR
		else:
			self.y = 10
		self.line_height = 15
	def bottom_print(self,screen, textString):
		textBitmap = self.font.render(textString, True, (0,0,0))
		global WH
		self.x = 10
		h = 20
		try:
			h = int(self.font.size("width")[1])
		except:
			pass
		self.y = int(WH-h-5)
		print self.y
		screen.blit(textBitmap, [self.x, self.y])
		pygame.display.flip()
class DeadzoneWidget:
	def __init__(self, total_dims, deadzone):
		self.total_dims = total_dims
		self.dz_x = deadzone[0]
		self.dz_y = deadzone[1]
	def draw(self, screen):
		screen.blit()

######################
## INITIAL SEQUENCE ##

## LOADING shape files
abort = load_shapes(SHAPES_DIRECTORY)
if abort:
	L.error("Could not find any shape template in [%s]",SHAPES_DIRECTORY)
	sys.exit(1)
## END LOADING shape files

## LOADING config and overwriting defaults
if not os.path.exists(CONFIG_FILE_PATH) or not os.path.isfile(CONFIG_FILE_PATH):
	# if no config file is available, force to show the calibration wizard
	L.info("no config file found. Opening the calibration screen next")
	MAINTENANCE = 11
else:
	c = None
	try:
		f = open(CONFIG_FILE_PATH, 'r')
		c = simplejson.load(f)
		f.close()
	except Exception:
		L.warning("Could not load config file [%s]",CONFIG_FILE_PATH)
		set_config()

	if c is not None:
		try:
			# frame sizes
			if int(c['window_w']) >= FRAME_SIZE_LIMIT[0][0] and int(c['window_w']) <= FRAME_SIZE_LIMIT[0][1]:
				WW = int(c['window_w'])
			# L.debug("loaded frame dimensions [%i,%i]",WW, WH)
			if int(c['window_h']) >= FRAME_SIZE_LIMIT[1][0] and int(c['window_h']) <= FRAME_SIZE_LIMIT[1][1]:
				WH = int(c['window_h'])
		except:
			L.warning("error loading window dimensions from config file, falling back to default")
		try:
			# find the last used VIZ Screen in the given viz list
			if len(SHAPES) > 0:
				for i,x in enumerate(SHAPES):
					if x["KEY"] == c['initial_screen']:
						cycle_viz(x["KEY"])
						L.debug("Initial viz set to [%s]", x["KEY"])
		except:
			L.warning("could not find initial viz setting in config file, falling back to default")
		try:
			L.debug("loading controls indeces")

			L.debug("c['controls']['PAD_INDEX']=[%s]", c['controls']['PAD_INDEX'] )
			if c['controls']['PAD_INDEX'] in range(0, 99):
				controls['PAD_INDEX'] = int(c['controls']['PAD_INDEX'])
				
			L.debug("c['controls']['acc']=[%s]", c['controls']['acc'] )
			if c['controls']['acc'] in range(0, 99):
				controls['acc'] = int(c['controls']['acc'])
				
			L.debug("c['controls']['brk']=[%s]", c['controls']['brk'] )
			if c['controls']['brk'] in range(0, 99):
				controls['brk'] = int(c['controls']['brk'])

			L.debug("c['controls']['steer']=[%s]", c['controls']['steer'] )
			if c['controls']['steer'] in range(0, 99):
				controls['steer'] = int(c['controls']['steer'])
		except:
			L.warning("could not find pad control mappings in config file, falling back to default")

		try:
			if c['color_acc']:
				colors["ACC"] = c['color_acc']
				L.debug("loaded acceleration color mapping [%s]",colors["ACC"])

			if c['color_brk']:
				colors["BRK"] = c['color_brk']
				L.debug("loaded break color mapping [%s]",colors["BRK"])
				
			if c['color_steer']:
				colors["STEER"] = c['color_steer']
				L.debug("loaded steering color mapping [%s]",colors["STEER"])

			if c['color_bg']:
				colors["BG"] = c['color_bg']
				L.debug("loaded background color mapping [%s]",colors["BG"])
		except Exception as e:
			L.warning("could not find color mappings in config file, falling back to default")

		try:
			if int(c['PRINT_DEBUGS_ON']) == 1:
				PRINT_DEBUGS_ON = True
				L.debug("loaded debugs print flag = [%s]",str(PRINT_DEBUGS_ON))
		except Exception as e:
			L.warning("could not load debug print flag in config file, falling back to default")


		try:
			if int(c['prepaint']) == 0:
				GREY_PREPAINT = False
				L.debug("loaded grey prepaint setting = [%s]",str(GREY_PREPAINT))
		except Exception as e:
			L.warning("could not find prepaint setting in config file, falling back to default")

		try:
			if float(c['deadzone'])>=0.0 and float(c['deadzone'])<=0.9:
				DEADZONE = float(c['deadzone'])
				L.debug("loaded deadzone setting [%s]", str(DEADZONE))
		except Exception as e:
			L.warning("could not find deadzone setting in config file, falling back to default")
## END LOADING config

pygame.init()
screen = pygame.display.set_mode([WW, WH], pygame.RESIZABLE | pygame.DOUBLEBUF)
screen.set_alpha(None)	## speedup
pygame.display.set_caption("Padviz")
pygame.joystick.init()
L.info("detected pads [%u]", pygame.joystick.get_count())
joystick = pygame.joystick.Joystick(controls['PAD_INDEX'])
joystick.init()
cycle_viz(None)	## initially load the first viz
try:
	APP_LOOP = True
	while APP_LOOP == True:
		event = pygame.event.wait()

		if event.type == pygame.VIDEORESIZE:
			frame_resize(event)
			cycle_viz(None)	# reloading the VIZ COORDS
			continue

		elif event.type==pygame.QUIT or (event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE):
			L.debug("pygame.QUIT")
			set_config()
			APP_LOOP = False
		
		elif event.type==pygame.JOYAXISMOTION or event.type==pygame.JOYBALLMOTION or event.type==pygame.JOYHATMOTION:
			VALUE_STEER = float(joystick.get_axis(controls['steer']))

		elif event.type==pygame.JOYBUTTONUP or event.type==pygame.JOYBUTTONDOWN:
			VALUE_ACC = joystick.get_button(controls['acc'])
			VALUE_BRK = joystick.get_button(controls['brk'])

		elif event.type == pygame.MOUSEMOTION:
			# setting the SQARE lenght, which is used to calculate the topbar buttons positioning
			SQR = int(WW/len(TOPBAR_BUTTONS))
			EV_Y = event.pos[1]
			EV_X = event.pos[0]

			## determing if the mouse is in the hover zone of the topbar
			if TOPBAR_AREA_HOVERS is False and EV_Y <= SQR:
				TOPBAR_AREA_HOVERS = True	# PAINT THE MOUSE HOVER TOPBAR
				# it only gets painted once! no repaints needed here
				pygame.draw.rect(screen, DEFAULT_COLORS["TOPBAR_BACKGROUND"], [(0,0),(WW,SQR)], 0)
				pygame.draw.line(screen, DEFAULT_COLORS["GRAY"], [0,SQR], [WW, SQR], 1)

				# painting the topbar buttons
				for i,b in enumerate(TOPBAR_BUTTONS):
					# pygame.draw.rect(screen, DEFAULT_COLORS["TOPBAR_BACKGROUND"], [ (SQR*int(i), 0), (SQR, SQR) ], 0)

					# ## TODO: hover over specific square! 
					# if EV_X >= SQR*int(i) :
					# # pygame.draw.rect(screen, DEFAULT_COLORS["TOPBAR_BACKGROUND"], [ (SQR*int(i), 0), (SQR, SQR) ], 0)
						# pygame.draw.rect(screen, DEFAULT_COLORS["TOPBAR_BACKGROUND_HOVER"], [(SQR*int(i), 0),(SQR,SQR)], 0)
					try:
						# images are auto centered since saved as quad
						surf = pygame.image.load(b["path"])
						# surf = pygame.transform.scale(surf, (SQR, SQR))
						surf = pygame.transform.smoothscale(surf, (SQR, SQR))
						irect = surf.get_rect()
						screen.blit(surf, [ (SQR*int(i), 0), (SQR, SQR) ])
					except Exception as e:
						print e
						# pass

				## when the topbar is show, on joystick events, the topbar will flicker since the whole screen gets repainted
				# with clip setting we limit the screen repaint area to all below the topbar
				screen.set_clip(pygame.Rect(0,SQR+1,WW,WH))
				pygame.display.flip()

			elif TOPBAR_AREA_HOVERS is True and EV_Y > SQR:
				TOPBAR_AREA_HOVERS = False	# HIDE
				## resetting the clipped area back to the whole window screen
				screen.set_clip(pygame.Rect(0,0,WW,WH))
				continue

		# if curser hovers topbar and a button was clicked
		elif event.type == pygame.MOUSEBUTTONDOWN and TOPBAR_AREA_HOVERS is True:

			# print pygame.mouse.get_pressed()		# 0 = Left click, 1 = scroll click, 2 = right click
			# determine pressed mousebutton
			button = 0
			try:
				button = pygame.mouse.get_pressed().index(1)
			except Exception as e:
				pass

			##### BUTTONS INTERACTION
			EV_X = event.pos[0]
			EV_Y = event.pos[1]
			# detect which buttons was clicked
			for i,c in enumerate(TOPBAR_BUTTONS):
				AR = [ (SQR*int(i), 0), (SQR*int(i+1), SQR) ]
				if TOPBAR_AREA_HOVERS and EV_X > AR[0][0] and EV_X <= AR[1][0] and EV_Y > AR[0][1] and EV_Y <= AR[1][1]:
					if c["command"] == "VIZ_CYCLE_PREV":
						# pygame.event.set_allowed(None)	# TODO: block multiclicks during time.sleep()
						cycle_viz(-1)
						# pygame.event.set_blocked(None)		# TODO: allow events again
					elif c["command"] == "VIZ_CYCLE_NEXT":
						# pygame.event.set_allowed(None)	# TODO: block multiclicks during time.sleep()
						cycle_viz(+1)
						# pygame.event.set_blocked(None)		# TODO: allow events again
					elif c["command"] == "PRINT_DEBUGS_ON":
						PRINT_DEBUGS_ON = not PRINT_DEBUGS_ON
					elif c["command"] == "DEADZONE":
						MAINTENANCE = 12
					elif c["command"] == "CALIBRATION":
						MAINTENANCE = 11
					elif c["command"] == "GREY_PREPAINT":
						GREY_PREPAINT = not GREY_PREPAINT
					elif c["command"] == "CYCLE_COLORS_ACC":
						if button == 0:
							colors["ACC"] = ( randint(0,255), randint(0,255), randint(0,255) )
						elif button == 2:
							colors["ACC"] = DEFAULT_COLORS["ACC"]
					elif c["command"] == "CYCLE_COLORS_BRK":
						if button == 0:
							colors["BRK"] = ( randint(0,255), randint(0,255), randint(0,255) )
						elif button == 2:
							colors["BRK"] = DEFAULT_COLORS["BRK"]
					elif c["command"] == "CYCLE_COLORS_STEER":
						if button == 0:
							colors["STEER"] = ( randint(0,255), randint(0,255), randint(0,255) )
						elif button == 2:
							colors["STEER"] = DEFAULT_COLORS["STEER"]
					elif c["command"] == "CYCLE_COLORS_BG":
						if button == 0:
							colors["BG"] = ( randint(0,255), randint(0,255), randint(0,255) )
						elif button == 2:
							colors["BG"] = DEFAULT_COLORS["BG"]

		#################
		#### DRAWING ####
		screen.fill(colors["BG"])

		if shape() in ["TRAPEZ", "DEFAULT", "CATEYE", "ANOTHEREYE", "THREEFLICKS", "DIAMONDS", "FIFEFLICKS"]:
			if int(VALUE_BRK):
				pygame.draw.polygon(screen, colors['BRK'], COO["BRK"], 0)
			elif GREY_PREPAINT:
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["BRK"], 0)
			
			if int(VALUE_ACC):
				pygame.draw.polygon(screen, colors['ACC'], COO["ACC"], 0)
			elif GREY_PREPAINT:
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["ACC"], 0)

		if shape() == "DEFAULT":
			if GREY_PREPAINT:
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["RIGHT"], 0)
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["LEFT"], 0)
			if VALUE_STEER > DEADZONE:
				#RIGHT
				r = (1/(1-DEADZONE))*(VALUE_STEER-DEADZONE)
				pygame.draw.polygon(screen, colors['STEER'], [COO["RIGHT"][0], (( (float(COO["RIGHT"][1][0])-float(COO["RIGHT"][0][0]))*r )+float(COO["RIGHT"][0][0]),float(COO["RIGHT"][1][1])), COO["RIGHT"][2] ], 0)
			elif VALUE_STEER < -DEADZONE:
				#LEFT
				r = (1/(1-DEADZONE))*(VALUE_STEER+DEADZONE)
				pygame.draw.polygon(screen, colors['STEER'], [COO["LEFT"][0], ((( (float(COO["LEFT"][0][0])-float(COO["LEFT"][1][0]))*r )+float(COO["LEFT"][0][0])),float(COO["LEFT"][1][1])), COO["LEFT"][2] ], 0)

		elif shape() == "TRAPEZ":
			if GREY_PREPAINT:
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["RIGHT"], 0)
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["LEFT"], 0)
			if VALUE_STEER > DEADZONE:
				#RIGHT
				r = (1/(1-DEADZONE))*(VALUE_STEER-DEADZONE)
				pygame.draw.polygon(screen, colors['STEER'],(COO["RIGHT"][0], ((((COO["RIGHT"][1][0]-COO["RIGHT"][0][0])*r ) + COO["RIGHT"][0][0]),(((COO["RIGHT"][1][1]-COO["RIGHT"][0][1])*r ) +COO["RIGHT"][0][1])), ((((COO["RIGHT"][1][0]-COO["RIGHT"][0][0])*r  )+COO["RIGHT"][0][0]),(((COO["RIGHT"][1][1]-COO["RIGHT"][0][1])*(1-r) )+COO["RIGHT"][1][1]))  ,COO["RIGHT"][2]), 0)
			elif VALUE_STEER < -DEADZONE:
				#LEFT
				r = ((1/(1-DEADZONE))*(VALUE_STEER+DEADZONE))+1
				pygame.draw.polygon(screen, colors['STEER'], (COO["LEFT"][0], ((((COO["LEFT"][0][0]-COO["LEFT"][1][0])*r)+COO["LEFT"][1][0]),(((COO["LEFT"][1][1]-COO["LEFT"][0][1])*(1-r))+COO["LEFT"][0][1])),(((COO["LEFT"][0][0]-COO["LEFT"][1][0])*r)+COO["LEFT"][1][0], ((COO["LEFT"][1][1]-COO["LEFT"][0][1])*r)+(COO["LEFT"][1][1])), COO["LEFT"][2]), 0)

		elif shape() == "CATEYE":
			if GREY_PREPAINT:
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["RIGHT"], 0)
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["LEFT"], 0)
			if VALUE_STEER > DEADZONE:
				#RIGHT
				r = (1/(1-DEADZONE))*(VALUE_STEER-DEADZONE)
				pygame.draw.polygon(screen, colors['STEER'], [COO["RIGHT"][0],(( (float(COO["RIGHT"][1][0])-float(COO["RIGHT"][3][0]))*r )+float(COO["RIGHT"][3][0]),float(COO["RIGHT"][1][1])), COO["RIGHT"][2],COO["RIGHT"][3]], 0)
			elif VALUE_STEER < -DEADZONE:
				r = 1+(1/(1-DEADZONE))*(VALUE_STEER+DEADZONE)
				pygame.draw.polygon(screen, colors['STEER'], [COO["LEFT"][0], ((( float(COO["LEFT"][3][0])-float(COO["LEFT"][1][0]) )*r ) + (float(COO["LEFT"][1][0])),float(COO["LEFT"][1][1])), COO["LEFT"][2],COO["LEFT"][3]], 0)

		elif shape() == "ANOTHEREYE":
			if GREY_PREPAINT:
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["RIGHT"], 0)
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["LEFT"], 0)
			if VALUE_STEER > DEADZONE:
				#RIGHT
				r = (1/(1-DEADZONE))*(VALUE_STEER-DEADZONE)
				pygame.draw.polygon(screen, colors['STEER'], [COO["RIGHT"][0],(( (float(COO["RIGHT"][1][0])-float(COO["RIGHT"][3][0]))*r )+float(COO["RIGHT"][3][0]),float(COO["RIGHT"][1][1])), COO["RIGHT"][2],COO["RIGHT"][3]], 0)
			elif VALUE_STEER < -DEADZONE:
				r = 1+(1/(1-DEADZONE))*(VALUE_STEER+DEADZONE)
				pygame.draw.polygon(screen, colors['STEER'], [COO["LEFT"][0], ((( float(COO["LEFT"][3][0])-float(COO["LEFT"][1][0]) )*r ) + (float(COO["LEFT"][1][0])),float(COO["LEFT"][1][1])), COO["LEFT"][2],COO["LEFT"][3]], 0)

		elif shape() == "THREEFLICKS":
			if GREY_PREPAINT:
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["LEFT_3"], 0)
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["LEFT_2"], 0)
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["LEFT_1"], 0)
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["RIGHT_1"], 0)
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["RIGHT_2"], 0)
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["RIGHT_3"], 0)
			# LEFT
			if VALUE_STEER < -DEADZONE:
				r = ((1/(1-DEADZONE))*(VALUE_STEER+DEADZONE))+1
				if r<=0.05:
					pygame.draw.polygon(screen, colors['STEER'], COO["LEFT_3"], 0)
				if r<=0.33:
					pygame.draw.polygon(screen, colors['STEER'], COO["LEFT_2"], 0)
				if r<=0.66:
					pygame.draw.polygon(screen, colors['STEER'], COO["LEFT_1"], 0)
			# RIGHT
			if VALUE_STEER > DEADZONE:
				r = (1/(1-DEADZONE))*(VALUE_STEER-DEADZONE)
				if r>=0.33:
					pygame.draw.polygon(screen, colors['STEER'], COO["RIGHT_1"], 0)
				if r>=0.66:
					pygame.draw.polygon(screen, colors['STEER'], COO["RIGHT_2"], 0)
				if r>=0.95:
					pygame.draw.polygon(screen, colors['STEER'], COO["RIGHT_3"], 0)

		elif shape() == "FIFEFLICKS":
			if GREY_PREPAINT:
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["LEFT_1"], 0)
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["LEFT_2"], 0)
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["LEFT_3"], 0)
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["LEFT_4"], 0)
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["LEFT_5"], 0)
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["RIGHT_1"], 0)
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["RIGHT_2"], 0)
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["RIGHT_3"], 0)
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["RIGHT_4"], 0)
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["RIGHT_5"], 0)
			# LEFT
			if VALUE_STEER < -DEADZONE:
				r = ((1/(1-DEADZONE))*(VALUE_STEER+DEADZONE))+1
				if r<=0.1:
					pygame.draw.polygon(screen, colors['STEER'], COO["LEFT_5"], 0)
				if r<=0.3:
					pygame.draw.polygon(screen, colors['STEER'], COO["LEFT_4"], 0)
				if r<=0.5:
					pygame.draw.polygon(screen, colors['STEER'], COO["LEFT_3"], 0)
				if r<=0.7:
					pygame.draw.polygon(screen, colors['STEER'], COO["LEFT_2"], 0)
				if r<=0.9:
					pygame.draw.polygon(screen, colors['STEER'], COO["LEFT_1"], 0)
			# RIGHT
			if VALUE_STEER > DEADZONE:
				r = (1/(1-DEADZONE))*(VALUE_STEER-DEADZONE)
				if r>=0.1:
					pygame.draw.polygon(screen, colors['STEER'], COO["RIGHT_1"], 0)
				if r>=0.3:
					pygame.draw.polygon(screen, colors['STEER'], COO["RIGHT_2"], 0)
				if r>=0.5:
					pygame.draw.polygon(screen, colors['STEER'], COO["RIGHT_3"], 0)
				if r>=0.7:
					pygame.draw.polygon(screen, colors['STEER'], COO["RIGHT_4"], 0)
				if r>=0.9:
					pygame.draw.polygon(screen, colors['STEER'], COO["RIGHT_5"], 0)

		elif shape() == "DIAMONDS":
			if GREY_PREPAINT:
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["LEFT_ACC_1"], 0)
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["LEFT_ACC_2"], 0)
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["LEFT_ACC_3"], 0)

				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["LEFT_BRK_1"], 0)
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["LEFT_BRK_2"], 0)
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["LEFT_BRK_3"], 0)
				
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["RIGHT_ACC_1"], 0)
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["RIGHT_ACC_2"], 0)
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["RIGHT_ACC_3"], 0)

				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["RIGHT_BRK_1"], 0)
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["RIGHT_BRK_2"], 0)
				pygame.draw.polygon(screen, DEFAULT_COLORS['LIGHTGRAY'], COO["RIGHT_BRK_3"], 0)
			# LEFT
			if VALUE_STEER < -DEADZONE:
				r = ((1/(1-DEADZONE))*(VALUE_STEER+DEADZONE))+1
				if r<=0.05:
					pygame.draw.polygon(screen, colors['ACC'] if int(VALUE_ACC) else colors['STEER'], COO["LEFT_ACC_3"], 0)
					pygame.draw.polygon(screen, colors['BRK'] if int(VALUE_BRK) else colors['STEER'], COO["LEFT_BRK_3"], 0)
				if r<=0.33:
					pygame.draw.polygon(screen, colors['ACC'] if int(VALUE_ACC) else colors['STEER'], COO["LEFT_ACC_2"], 0)
					pygame.draw.polygon(screen, colors['BRK'] if int(VALUE_BRK) else colors['STEER'], COO["LEFT_BRK_2"], 0)
				if r<=0.66:
					pygame.draw.polygon(screen, colors['ACC'] if int(VALUE_ACC) else colors['STEER'], COO["LEFT_ACC_1"], 0)
					pygame.draw.polygon(screen, colors['BRK'] if int(VALUE_BRK) else colors['STEER'], COO["LEFT_BRK_1"], 0)
			# RIGHT
			if VALUE_STEER > DEADZONE:
				r = (1/(1-DEADZONE))*(VALUE_STEER-DEADZONE)
				if r>=0.33:
					pygame.draw.polygon(screen, colors['ACC'] if int(VALUE_ACC) else colors['STEER'], COO["RIGHT_ACC_1"], 0)
					pygame.draw.polygon(screen, colors['BRK'] if int(VALUE_BRK) else colors['STEER'], COO["RIGHT_BRK_1"], 0)
				if r>=0.66:
					pygame.draw.polygon(screen, colors['ACC'] if int(VALUE_ACC) else colors['STEER'], COO["RIGHT_ACC_2"], 0)
					pygame.draw.polygon(screen, colors['BRK'] if int(VALUE_BRK) else colors['STEER'], COO["RIGHT_BRK_2"], 0)
				if r>=0.95:
					pygame.draw.polygon(screen, colors['ACC'] if int(VALUE_ACC) else colors['STEER'], COO["RIGHT_ACC_3"], 0)
					pygame.draw.polygon(screen, colors['BRK'] if int(VALUE_BRK) else colors['STEER'], COO["RIGHT_BRK_3"], 0)


		# DEBUGS
		if PRINT_DEBUGS_ON:
			textPrint = TextPrint()
			textPrint.reset()
			textPrint.screenprint(screen, "CURRENT VISUALIZER: %s" % shape() )
			textPrint.screenprint(screen, "DEBUG PAD PRINT VALUES" )
			pads = pygame.joystick.get_count()
			for pad in range(pads):
				current_pad = pygame.joystick.Joystick(pad)
				current_pad.init()
				textPrint.screenprint(screen, "pad: {}".format(joystick.get_name()) )

				for ax in range( current_pad.get_numaxes() ):
					axis = current_pad.get_axis( ax )
					if axis > DEADZONE or axis < (-DEADZONE):
						textPrint.screenprint(screen, "Axis {} value: {:>6.3f}".format(ax, axis) )
					
				for b in range( current_pad.get_numbuttons() ):
					butt = current_pad.get_button( b )
					if butt:
						textPrint.screenprint(screen, "Button {:>2} value: {}".format(b,butt) )

				for h in range( current_pad.get_numhats() ):
					hat = current_pad.get_hat( h )
					if bool(hat[0]) or bool(hat[1]):
						textPrint.screenprint(screen, "Hat {} value: {}".format(h, str(hat)) )
		
		pygame.display.flip() 

		# CALIBRATION wizard
		if MAINTENANCE == 11:
			TOPBAR_AREA_HOVERS = False
			screen.set_clip(pygame.Rect(0,0,WW,WH))

			newcalibration = { 'PAD_INDEX':0, 'acc': None, 'brk': None, 'steer': None }

			screen.fill(DEFAULT_COLORS['WHITE'])

			textPrint = TextPrint()
			textPrint.reset()
			textPrint.screenprint(screen, "CALIBRATION WIZARD | press [ESCAPE] to cancel")
			textPrint.screenprint(screen, "")
			pygame.display.flip()

			CALIBRATION_WIZARD_LOOP = True
			while CALIBRATION_WIZARD_LOOP:

				L.debug("found pads [%i]", pygame.joystick.get_count() )
				L.debug("determine which pad to use for calibration")

				if pygame.joystick.get_count() > 1:
					textPrint.screenprint(screen, "multiple pads are connected to your system")
					textPrint.screenprint(screen, "press any button on your active pad")
					pygame.display.flip()


					valid = False
					while not valid:
						tmp = pygame.event.wait()
						if tmp.type == pygame.KEYDOWN and tmp.key == pygame.K_ESCAPE or tmp.type == pygame.QUIT:
							CALIBRATION_WIZARD_LOOP = False
							break
						elif tmp.type == pygame.JOYBUTTONDOWN:
							for pad in range(pygame.joystick.get_count()):
								J = pygame.joystick.Joystick(pad)
								J.init()

								for b in range( J.get_numbuttons() ):
									butt = J.get_button( b )
									if butt:
										L.debug(str.format("identified pad [{0}] ID=[{1}]", J.get_name(), str(J.get_id())))
										newcalibration['PAD_INDEX'] = pad
										textPrint.screenprint(screen, str.format("active pad [{0}] ID=[{1}]", J.get_name(), str(J.get_id())))
										textPrint.screenprint(screen, "")
										pygame.display.flip()
										valid = True

				if not CALIBRATION_WIZARD_LOOP:
					MAINTENANCE = 0
					textPrint.screenprint(screen, "CALIBRATION WIZARD CANCELLED")
					CALIBRATION_WIZARD_LOOP = False
					break


				pygame.joystick.init()
				joystick = pygame.joystick.Joystick(newcalibration['PAD_INDEX'])
				joystick.init()

				## ACCELERATION SETUP ###########################
				textPrint.screenprint(screen, "press your acceleration-button")
				pygame.display.flip()
				valid = False
				while not valid:
					tmp = pygame.event.wait()
					if tmp.type == pygame.KEYDOWN and tmp.key == pygame.K_ESCAPE or tmp.type == pygame.QUIT:
						CALIBRATION_WIZARD_LOOP = False
						valid = True
						break
					elif tmp.type == pygame.JOYBUTTONDOWN:
						## get joystick-button-id
						for i in range( joystick.get_numbuttons()):
							button = joystick.get_button(i)
							if( button == 1):
								newcalibration['acc'] = i
								textPrint.screenprint(screen, "acceleration = button[%s]" % str(i))
								valid = True
								break

				if not CALIBRATION_WIZARD_LOOP:
					MAINTENANCE = 0
					textPrint.screenprint(screen, "CALIBRATION WIZARD CANCELLED")
					CALIBRATION_WIZARD_LOOP = False
					break

				## BREAK SETUP ###########################
				textPrint.screenprint(screen, "press your break-button")
				pygame.display.flip()

				valid = False
				while not valid:
					tmp = pygame.event.wait()
					if tmp.type == pygame.KEYDOWN and tmp.key == pygame.K_ESCAPE or tmp.type == pygame.QUIT:
						CALIBRATION_WIZARD_LOOP = False
						valid = True
						break
					elif tmp.type == pygame.JOYBUTTONDOWN:
						## get joystick-button-id
						for i in range( joystick.get_numbuttons()):
							## don't get the same key as acc
							if(i != newcalibration['acc']):	
								button = joystick.get_button(i)
								if( button == 1):
									newcalibration['brk'] = i
									textPrint.screenprint(screen, "break = button[%s]" % str(i))
									valid = True
									break

				if not CALIBRATION_WIZARD_LOOP:
					MAINTENANCE = 0
					textPrint.screenprint(screen, "CALIBRATION WIZARD CANCELLED")
					CALIBRATION_WIZARD_LOOP = False
					break

				# ## STEERING SETUP ###########################
				textPrint.screenprint(screen, "move your steering-axis completely left or right")
				pygame.display.flip()

				a = {}	## will cache all axis values in a dictionary
				done = False
				while not done:
					tmp = pygame.event.wait()
					if tmp.type == pygame.KEYDOWN and tmp.key == pygame.K_ESCAPE or tmp.type == pygame.QUIT:
						CALIBRATION_WIZARD_LOOP = False
						valid = True
						break
					elif tmp.type == pygame.JOYAXISMOTION:
						for i in range( joystick.get_numaxes() ):
							ax = joystick.get_axis(i)
							t = "AXIS_"+str(i)	## dictionary template

							# Because all axis will be checked in one loop/trigger, values have to be cached and compared to each current value
							if not len(a):	# first cycle - array is empty
								a[t] = ax
							else:
								try:
									if a[t] == ax:
										# value is the same as last loop run
										# delete this part of the array
										del a[t]
									else:
										# value has changed
										# check if the value is above or below certain threshold
										if ax >= 0.7 or ax <= -0.7:
											newcalibration['steer'] = i
											textPrint.screenprint(screen, "steer = axis[%s]" % str(i))
											done = True
										else:
											# if the value is still not in a wanted range, update the list value
											a[t] = ax
								except KeyError:
									pass
				
				if not CALIBRATION_WIZARD_LOOP:
					MAINTENANCE = 0
					textPrint.screenprint(screen, "CALIBRATION WIZARD CANCELLED")
					break

				textPrint.screenprint(screen, "CALIBRATION WIZARD DONE")
				pygame.display.flip()

				MAINTENANCE = 0
				controls = newcalibration	## adopt new controls settings
				set_config()
				time.sleep(1)
				CALIBRATION_WIZARD_LOOP = False

		# DEADZONE SCREEN
		elif MAINTENANCE == 12:
			L.info("entered deadzone widget")
			TOPBAR_AREA_HOVERS = False
			pygame.event.set_allowed([pygame.MOUSEBUTTONDOWN])
			screen.set_clip(pygame.Rect(0,0,WW,WH))

			margin = 50
			md = ((margin, margin*2),(WW-(margin*2), margin))
			STEER = 0
			textPrint = TextPrint()
			SETTINGS_LOOP = True
			while SETTINGS_LOOP:
				screen.fill(colors["BG"])
				textPrint.screenprint_buf(screen, "Pad steering deadzone | press [ESCAPE] to exit", margin, margin/2 )

				# full rect dimension of deadzone widget
				pygame.draw.rect(screen, (200,202,220), pygame.Rect( md ) )

				# real value of pad steering input
				pygame.draw.rect(screen, (200,1,38), pygame.Rect( md[0], ( md[1][0]*STEER, md[1][1]/2) ))	

				# calculated steering input including the deadzone
				d = (STEER-DEADZONE)*(md[1][0])*(md[1][0] / (md[1][0]- (md[1][0]*DEADZONE)) )
				if STEER >= DEADZONE:
					pygame.draw.rect(screen, (100,50,255), pygame.Rect( (md[0][0], md[0][1]+(md[1][1]/2)), ( d, md[1][1]/2) ))

				# min deadzone line
				pygame.draw.line(screen, (0,0,0), ( ( DEADZONE*md[1][0])+md[0][0] ,md[0][1]-(md[1][1]/2)), ((DEADZONE*md[1][0])+md[0][0] , md[1][1]+md[0][1]))
				textPrint.screenprint_buf(screen, str(round(DEADZONE, 3)), DEADZONE*md[1][0]+md[0][0]+3, md[0][1]-(md[1][1]/2) )

				# draw the pointing deadzone
				mpos = pygame.mouse.get_pos()
				if mpos[0] in range(md[0][0], (md[1][0]+md[0][0]) ) and mpos[1] in range(md[0][1], (md[1][1]+md[0][1])) :
					d = float( float(mpos[0]-md[0][0]) / md[1][0] )
					pygame.draw.line(screen, (100,100,100), (mpos[0], md[0][1]), (mpos[0], md[0][1]+md[1][1]+(md[1][1]/2) ))
					textPrint.reset()
					textPrint.screenprint_buf(screen, str(round(d, 3)), mpos[0]+3, md[0][1]+md[1][1])

				se = pygame.event.wait()
				if se.type == pygame.QUIT or (se.type == pygame.KEYDOWN and se.key == pygame.K_ESCAPE):
					SETTINGS_LOOP = False
				elif se.type==pygame.JOYAXISMOTION or se.type==pygame.JOYBALLMOTION or se.type==pygame.JOYHATMOTION:
					STEER = abs(float(joystick.get_axis(controls['steer'])))
				elif se.type==pygame.MOUSEBUTTONDOWN or se.type==pygame.MOUSEMOTION:
					# set the deadzone if clicked in the deadzone region
					if bool(pygame.mouse.get_pressed()[0]) or bool(pygame.mouse.get_pressed()[1]) or bool(pygame.mouse.get_pressed()[2]):
						if mpos[0] in range(md[0][0], (md[1][0]+md[0][0]) ) and mpos[1] in range( md[0][1], (md[1][1]+md[0][1]) ):
							d = float( float(mpos[0]-md[0][0]) / md[1][0] )
							DEADZONE = round(d, 3)
							L.info("Changed deadzone value to [%s]" % str(DEADZONE) )

				elif se.type == pygame.VIDEORESIZE:
					frame_resize(se)
					md = ((margin, margin*2),(WW-(margin*2), margin))
					continue

				pygame.display.flip()
				pygame.event.clear()

			pygame.event.set_blocked([])
			set_config()
			MAINTENANCE = 0

except Exception as e:
	L.error(e)
	raise
finally:
	pygame.quit()