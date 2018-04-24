

# define specific view for the webcloient here

import typing
# import qailib.common.base as base

# import qailib.transcryptlib.htmlelements as html
import qailib.transcryptlib.widgets as widgets
import qailib.transcryptlib.SVGlib as SVGlib


class RadarView(widgets.BasicView):
    def __init__(self, contr: widgets.base_controller,
                 parent: widgets.base_widget,
                 idstr: str,
                 attrdct: dict,
                 jsel) -> None:
        attrdct = attrdct or {}
        attrdct['height'] = attrdct['width'] = '100%'
        attrdct['class'] = 'switchview-cls'
        super().__init__(contr, parent, idstr, attrdct, jsel)
        # size_tup = ('100%', '100%')
        size_tup = None
        self.svg = SVGlib.svg(self, 'scosvg', attrdct, None, size_tup)

    def set_radardata(self, radarinfo: typing.List[typing.Tuple[str, int]]):
        """Display the radar data on the screen"""
        pass
