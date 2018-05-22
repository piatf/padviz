#WHAT and WHY?
The *Padviz*ualizer is a small UI tool, written in python2 with the pygame 1.9.3 library, which provides libSDL 2.0 bindings.
Using vectorgraphic templates it displays 2 dimensional polygons depending on your gamepad inputs.

Originally it was designed for Trackmania streams/videos so people can see what buttons or analog inputs you are pressing. 
Currently displayed inputs are limited to trackmania gameplay standards: Acceleration (digital), breaking (digital) and steering (analog).

#DEVELOPMENT
Please note, the tool is still in development, not too stable and very limited in it's use. 
There is no fixed development schedule. But I will try my best to respond and fix things that need fixing.

#ROADMAP
* analog input for acceleration or breaking
* autodetect pads in calibration
* color selection widget
* More intuitive UI for color selection, setting the deadzone, more responsive topbar
* OPTIMIZE sprite and preload UI graphics
* poly animations on input (popup, color transitions...)
* more (circlic) visualizer displays
* Frame delayed smoothing?
* allow keyboard input?
* antialiasing? > gfxdraw

#LICENSE
This application comes "AS IS". I don't serve any warranty for it. It is licensed under LGPL-3.0. For a detailed license description see the LICENSE.txt document. For a short summary see here https://tldrlegal.com/license/gnu-lesser-general-public-license-v3-(lgpl-3)

#FAQ
> why is the zip file still so big, despite the application being quite "small" ?
Since I programmed the application with python2 - python is a scripting language and uses an interpreter - the zipped package also contains the whole python interpreter and additional libraries, like 'pygame'. 
If you prefer to, you can also get the code and run it on your system, with your local python2 installation and necessary libraries.

> So why haven't you coded a c# application or - even better - an OBS plugin?
Because i'm stupid and lazy

> I haven't changed any configuration but the inputs suddenly won't show
One possible cause is, that you plugged or un-plugged another pad to your machine, next to the active one. A simple solution is to delete you config.json file and re-calibrate your inputs in the padviz application.

#DEVNOTES
- when bundling with py2exe, don't bundle all files into one 
- in each svg viz template always include a general padding

#KNOWN ISSUES
- Why won't the viz show some very short brakes or acceleration bits?
> I will probably not be able to fix this case with the padviz software. It depends on your pad driver. I was able to reproduce the described case with the default xbox pad driver. Using a custom driver you can resolve it by using increased polling rates. 

- When the padviz tool is out of focus, it won't dispaly any input values of the pad anymore.
> I'm currently investigating this one. 'Really not sure what causes this and I cannot reproduce it on my machine.
Reported for
	- windows 10 with ps3 controller
	- windows 10 with xbox one controller
	- windows 7  with xbox 360 controller

#LINKS
* [python27](https://www.python.org/download/releases/2.7/)
* [pygame](https://www.pygame.org/wiki/about)
* [libsdl](https://www.libsdl.org/)


##CHANGELOG v0.2.4
- FIX: on app start show the calibration screen, if no configuration file (config.json) exists in the directory
- FIX: if multiple pads are connected to your machine, the calibration wizard will notice the correct one