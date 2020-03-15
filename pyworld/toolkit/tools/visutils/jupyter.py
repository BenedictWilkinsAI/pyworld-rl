import plotly.offline as pyo
import plotly.graph_objs as go
# Set notebook mode to work in offline
#pyo.init_notebook_mode()

from ipywidgets import Image, Layout, VBox, HBox, interact, IntSlider, IntProgress, HTML, Output
import ipywidgets as widgets

from IPython.display import display, clear_output

import numpy as np
import math

from . import transform
from . import plot as vis_plot

from .plot import line_mode

try:
    from ipyevents import Event 
except:
    pass

try:
    from ipycanvas import Canvas, MultiCanvas
except:
    pass


class SimplePlot(vis_plot.SimplePlot):
    '''
        Wrapper around a plotly figure that allows offline updates in Jupyter.
    '''

    def __init__(self, x, y, *args, **kwargs):
        super(SimplePlot, self).__init__(x,y,*args,**kwargs)
        self.fig = go.FigureWidget(self.fig)
    
    def display(self):
        display(self.fig)

class DynamicPlot(SimplePlot):

    def __init__(self, x=[], y=[], update_after=100, *args, **kwargs):
        super(DynamicPlot, self).__init__(x,y,*args,**kwargs)
        self.__cachex = []
        self.__cachey = [] 
        self.__update_after = update_after

    def extend(self,x,y,trace=0):
        assert len(x) == len(y)
        assert trace == 0 # multiple traces not supported yet
        self.__cachex.extend(x)
        self.__cachey.extend(y)
        if len(self.__cachex) > self.__update_after:
            super(DynamicPlot,self).extend(self.__cachex, self.__cachey, trace=trace)
            self.__cachex.clear()          
            self.__cachey.clear()

def plot(x,y,mode=line_mode.line,legend=None,show=True):
    plot = SimplePlot(x,y,mode=mode,legend=legend)
    if show:
        plot.display()
    return plot

def dynamic_plot(x=[],y=[],mode=line_mode.line,legend=None,show=True):
    plot = DynamicPlot(x=x,y=y,mode=mode,legend=legend)
    if show:
        plot.display()
    return plot

def progress(iterator, info=None):
    f = IntProgress(min=0, max=len(iterator), step=1, value=0) # instantiate the bar
    print(info)
    display(f)
    for i in iterator:
        yield i
        f.value += 1

def scatter_image(x, y, images, scale=1, scatter_colour=None, line_colour=None):
    #images must be in NHWC format
    assert transform.isHWC(images)

    if transform.is_float(images):
        images = transform.to_integer(images)

    fig = go.FigureWidget(data=[dict(type='scattergl',x=x,y=y,mode='markers+lines',
                marker=dict(color=scatter_colour),
                line=dict(color=line_colour))])
    fig.layout.hovermode = 'closest'
    scatter = fig.data[0]

    #convert images to png format
    image_width = '{0}px'.format(int(images.shape[2] * scale))
    image_height = '{0}px'.format(int(images.shape[1] * scale))
    images = [transform.to_bytes(image) for image in images]

    image_widget = Image(value=images[0], 
                        layout=Layout(height=image_height, width=image_width))
    def hover_fn(trace, points, state):
        ind = points.point_inds[0]
        image_widget.value = images[ind]

    scatter.on_hover(hover_fn)
    #fig.show()
    #print("WHAT")

    box_layout = widgets.Layout(display='flex',flex_flow='row',align_items='center',width='100%')
    display(HBox([fig, image_widget], layout=box_layout)) #basically... this needs to be done in jupyter..?!]
    return fig, image_widget


class SimpleImage:

    def __init__(self, image, scale=1, interpolation=transform.interpolation.nearest):
        self.__scale = scale
        self.__interpolation = interpolation
        self.__image = self.transform(image)

        self.__canvas = Canvas(width=self.__image.shape[1], height=self.__image.shape[0], scale=1)
        self.__canvas.put_image_data(self.__image, 0, 0)  

    def transform(self, image):
        assert transform.isHWC(image)

        #TODO refactor..

        if transform.is_integer(image):
            image = transform.to_float(image)
        else:
            image = image.astype(np.float32) #must be float32...

        if image.shape[-1] != 3:
            image = transform.colour(image) #requires HWC float format...
        if self.__scale != 1:
            image = transform.scale(image, self.__scale, interpolation=self.__interpolation)

        return transform.to_integer(image) #finally transform to int

    def display(self):
        display(self.__canvas)

    def set_image(self, image):
        #TODO if this is live there might be problems... give the option of preprocessing via transform

        image = self.transform(image)
        assert image.shape == self.__image.shape #shapes must be equal after scaling
        self.__image = image
        self.__canvas.put_image_data(image)

    @property
    def widget(self):
        return self.__canvas

    def scale(self):
        raise NotImplementedError("TODO scale the image?")


def image(image, scale=1, interpolation=transform.interpolation.nearest, show=True):
    image_widget = SimpleImage(image, scale=scale, interpolation=interpolation)
    if show:
        image_widget.display()

    return image_widget

def images(images, scale=1, interpolation=transform.interpolation.nearest, show=True):
    print(images[0].shape)
    image_widget = SimpleImage(images[0], scale=scale, interpolation=interpolation)

    def slide(x):
        image_widget.set_image(images[x])

    interact(slide, x=IntSlider(min=0, max=len(images)-1, step=1, value=0))
    if show:
        image_widget.display()
    return image_widget



def mouse_hover(widget, callback):
    e = Event(source=widget, watched_events=['mousemove'])
    e.on_dom_event(callback)

class __IPyCanvasMouseMoveHandler:

    def __init__(self, canvas, callback, scale=1):
        self.px = self.py = 0
        self.callback = callback
        self.scale = scale
        self.canvas = canvas

    def __call__(self, x, y):
        x = min(max(int(x / self.scale), 0), int(self.canvas.width / self.scale -1))
        y = min(max(int(y / self.scale), 0), int(self.canvas.height / self.scale -1))
        if self.px == x and self.py == y:
            return
        self.callback(x, y)

class __GridSnap:

    def __init__(self, snap=(1,1)):
        self._snapx = snap[0]
        self._snapy = snap[1]
    
    def snap(self, x, y):
        x = int(x / self._snapx) * self._snapx
        y = int(y / self._snapy) * self._snapy

class __IPyEventMouseMoveHandler:

    def __init__(self, widget, callback, snap=(1,1), min_position=None, max_position=None):
        self.px = self.py = 0
        self._snapx, self._snapy = snap

        self.callback = callback
        self.widget = widget

        if max_position is None:
            self._maxx, self._maxy = widget.width, widget.height
        else:
            self._maxx, self._maxy = max_position

        if min_position is None:
            self._minx = self._miny = 0
        else:
            self._minx, self._miny = min_position

        mouse_hover(widget, self)

    def __call__(self, event):
        x, y = event['relativeX'] - 2, event['relativeY'] - 2
        x = min(max(int(x / self._snapx) * self._snapx, self._minx), self._maxx)
        y = min(max(int(y / self._snapy) * self._snapy, self._miny), self._maxy)

        if self.px == x and self.py == y:
            return

        self.px, self.py = x, y
        self.callback(x, y)

    @property
    def widget_width(self):
        return int(self.widget.width)
    
    @property
    def widget_height(self):
        return int(self.widget.height)

def image_roi(image, callback=lambda *_: None, box_shape=(4,4), snap=(1,1), scale=1, highlight_alpha=0.2, show=True):
    assert transform.isHWC(image)

    if transform.is_integer(image):
        image = transform.to_float(image)
    else:
        image = image.astype(np.float32) #must be float32...

    image = transform.colour(image) #requires HWC float format...
    image = transform.scale(image, scale, interpolation=transform.interpolation.nearest)
    
    image = transform.to_integer(image)

    canvas = MultiCanvas(2, width=image.shape[0], height=image.shape[1], scale=1)
    canvas[0].put_image_data(image, 0, 0)
    
    bw = box_shape[0] * scale
    bh = box_shape[1] * scale

    out = Output() #for printing stuff..

    @out.capture()
    def draw_callback(x, y):
        canvas[1].clear()
        canvas[1].fill_style = 'white'
        canvas[1].global_alpha = highlight_alpha
        canvas[1].fill_rect(x,y,bw,bh)
    
        canvas[1].global_alpha = 1.
        canvas[1].stroke_style = 'red'
        canvas[1].stroke_rect(x,y,bw,bh)

        callback(x,y)
    
    snap = (snap[0] * scale, snap[1] * scale)
    max_position = (canvas.width - bw, canvas.height - bh)
    mmh = __IPyEventMouseMoveHandler(canvas, draw_callback, snap=snap, max_position=max_position)
    if show:
        display(VBox([canvas,out]))

    return canvas, mmh