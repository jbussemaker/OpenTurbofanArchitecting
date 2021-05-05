"""
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Copyright: (c) 2020, Deutsches Zentrum fuer Luft- und Raumfahrt e.V.
Contact: jasper.bussemaker@dlr.de
"""

import math
from typing import *
from lxml import etree
from lxml.builder import E
from open_turb_arch.evaluation.architecture.flow import *
from open_turb_arch.evaluation.architecture.turbomachinery import *
from open_turb_arch.evaluation.architecture.architecture import TurbofanArchitecture

__all__ = ['ArchitectureVisualizer']


class ArchitectureVisualizer:
    """
    Turbofan architecture visualization using SVG. Note that although the evaluation module should in theory be
    independent of this code, unfortunately the visualization code at times is based ont he specific usage of the
    evaluation code by the architecting code.
    """

    _font = 'Georgia, Times New Roman'
    _font_size = 10
    _pt_to_px = 96./72.

    def __init__(self):
        self._def_elements = []

    def export_svg(self, architecture: TurbofanArchitecture, path: str):
        svg_el = self._render_svg(architecture)

        with open(path, 'wb') as fp:
            fp.write(etree.tostring(svg_el, encoding='utf-8', pretty_print=True))

    def _render_svg(self, architecture: TurbofanArchitecture) -> etree.Element:
        root = self._get_root_el()
        self._def_elements = []
        # total_width, total_height = 0, 0

        core_el, core_width, core_height = self._render_core(architecture)
        total_width, total_height = core_width, core_height
        root.append(self._translate(core_el, 0, .5*core_height))

        # # Some example elements
        # root.append(self._rect(0, 0, 100, 100, 'black', opacity=.1))
        # root.append(self._line(50, 130, 150, 150, 'red', stroke_width=2))
        # root.append(self._rect(110, 110, 100, 100, 'transparent', stroke_color='blue', stroke_width=5))
        # root.append(self._text('center test', 150, 50))
        # root.append(self._text('left test', 150, 70, direction=1))
        # root.append(self._text('right test', 150, 90, direction=-1))
        # root.append(self._text('upside down', 150, 30, rotation_deg=180))
        # root.append(self._text('vertical', 200, 100, rotation_deg=-90))

        if len(self._def_elements) > 0:
            root.insert(0, E.defs(*self._def_elements))

        root.attrib['viewBox'] = '0 0 %f %f' % (total_width, total_height)
        return root

    def _render_core(self, architecture: TurbofanArchitecture) -> Tuple[etree.Element, float, float]:
        """Renders the turbofan/turbojet core. Returns a group with anchor at center of core inlet."""
        total_width, total_height = 0, 0
        elements: List[Tuple[int, etree.Element]] = []

        # Drawing parameters
        spinner_length = 50
        compressor_height = 100
        flow_height_frac = .6
        burner_height = 50
        burner_length = 50
        compressor_length = (40, 70)  # length at 0%, length at 100%
        turbine_height = 120
        turbine_length = (70, 20)
        nozzle_length = 40
        nozzle_ratio = .8
        shaft_height = 3

        inner_stroke_width = .5
        stroke_width = 1

        # Colors from: https://www.materialui.co/colors
        # compressor_colors = ['#3F51B5', '#673AB7', '#9C27B0']
        # compressor_fill_colors = ['#7986CB', '#9575CD', '#BA68C8']
        # spinner_colors = ['#4FC3F7', '#0288D1']
        # burner_colors = ['#FFD54F', '#f44336']

        compressor_colors = ['#90A4AE', '#78909C', '#607D8B']
        compressor_fill_colors = ['#E0E0E0', '#BDBDBD', '#9E9E9E']
        spinner_colors = ['#CFD8DC', '#78909C']
        burner_colors = ['#F57C00', '#BF360C']

        shaft_color = {}
        shaft_x_start = {}
        shaft_x_end = {}

        # Define gradients
        spinner_gradient_id = 'spinner'
        spinner_color = 'url(#%s)' % spinner_gradient_id
        nozzle_color = spinner_color
        self._define_linear_gradient(spinner_gradient_id, [
            (0., spinner_colors[0], {}),
            (1., spinner_colors[1], {}),
        ], direction_deg=90)

        burner_gradient_id = 'burner'
        self._define_linear_gradient(burner_gradient_id, [
            (0., burner_colors[0], {}),
            (1., burner_colors[1], {}),
        ])

        # Compressor geometry
        n_compressors = len([c for c in architecture.get_elements_by_type(Compressor) if not self._is_fan(c)])
        compressor_height_fraction = (burner_height/compressor_height)**(1./n_compressors)
        if n_compressors > 3:
            raise RuntimeError('Currently only up to 3 compressors are supported!')

        # Turbine geometry
        n_turbines = len([t for t in architecture.get_elements_by_type(Turbine)])
        turbine_height_fraction = (turbine_height/burner_height)**(1./n_turbines)

        # Assume from inner (low-pressure) to outer (high-pressure), the shaft rpm increases
        shafts = sorted([s for s in architecture.get_elements_by_type(Shaft)], key=lambda s: s.rpm_design)

        # Draw inlet spinner
        # Path reference: https://developer.mozilla.org/en-US/docs/Web/SVG/Tutorial/Paths
        x = 0
        half_height = .5*compressor_height*flow_height_frac
        elements.append((0, self._path([
            'M %s,%s' % (x+spinner_length, -half_height),  # Start at upper right corner
            'C %s %s, %s %s, %s %s' % (  # Bezier curve
                x-10, -half_height*.5,  # First control point (upper side)
                x-10, half_height*.5,  # Second control point (lower side)
                x+spinner_length, half_height,  # End point
            ),
            'Z',  # Close the path
        ], fill_color=spinner_color, stroke_color=spinner_color, stroke_width=stroke_width)))

        total_width += spinner_length
        x += spinner_length

        # Get the starting element and draw the core flow elements
        arch_el = self._get_core_start(architecture)
        current_height = compressor_height
        i_compressor = 0
        outer_coords = []
        while True:
            if isinstance(arch_el, Compressor):
                end_height = current_height*compressor_height_fraction
                compression_frac = 1-((end_height-burner_height)/(compressor_height-burner_height))
                length = compressor_length[0]+compression_frac*(compressor_length[1]-compressor_length[0])

                # Determine color through shaft color
                color = compressor_colors[i_compressor+len(compressor_colors)-n_compressors]
                fill_color = compressor_fill_colors[i_compressor+len(compressor_colors)-n_compressors]
                i_shaft = [i for i, shaft in enumerate(shafts) if arch_el in shaft.connections]
                if len(i_shaft) != 1:
                    raise RuntimeError('Compressor assigned to 0 or more than 1 shafts: %r' % arch_el)
                i_shaft = i_shaft[0]
                if i_shaft in shaft_color:
                    color, fill_color = shaft_color[i_shaft]
                else:
                    shaft_color[i_shaft] = color, fill_color

                shaft_x_start[i_shaft] = min(shaft_x_start.get(i_shaft, 999999), x)
                shaft_x_end[i_shaft] = max(shaft_x_end.get(i_shaft, 0), x+length)

                # Draw polygons
                elements.append((1, self._poly([
                    (x, -.5*current_height*flow_height_frac),  # Left upper corner
                    (x+length, -.5*end_height*flow_height_frac),  # Right upper corner
                    (x+length, .5*end_height*flow_height_frac),  # Right lower corner
                    (x, .5*current_height*flow_height_frac),  # Left lower corner
                ], fill_color=fill_color, stroke_color=color, stroke_width=inner_stroke_width, closed=True)))
                elements.append((1, self._poly([
                    (x, -.5*current_height),  # Left upper corner
                    (x+length, -.5*end_height),  # Right upper corner
                    (x+length, .5*end_height),  # Right lower corner
                    (x, .5*current_height),  # Left lower corner
                ], stroke_color=color, stroke_width=stroke_width, closed=True)))

                if len(outer_coords) == 0:
                    outer_coords += [(x, .5*current_height)]
                outer_coords += [(x+length, .5*end_height)]

                # Prepare next drawing step
                total_height = max(total_height, current_height)
                current_height = end_height
                total_width += length
                x += length
                i_compressor += 1

            elif isinstance(arch_el, Burner):
                color = 'url(#%s)' % burner_gradient_id
                elements.append((0, self._rect(
                    x, -.5*burner_height, burner_length, burner_height,
                    fill_color=color, stroke_color=color, stroke_width=stroke_width)))

                outer_coords += [(x+burner_length, .5*burner_height)]
                x += burner_length
                total_width += burner_length

            elif isinstance(arch_el, Turbine):
                end_height = current_height*turbine_height_fraction
                expansion_frac = .5*((1-((current_height-burner_height)/(turbine_height-burner_height)))+
                                     (1-((end_height-burner_height)/(turbine_height-burner_height))))
                length = turbine_length[0]+expansion_frac*(turbine_length[1]-turbine_length[0])

                # Determine color from shaft color
                i_shaft = [i for i, shaft in enumerate(shafts) if arch_el in shaft.connections]
                if len(i_shaft) != 1:
                    raise RuntimeError('Turbine assigned to 0 or more than 1 shafts: %r' % arch_el)
                i_shaft = i_shaft[0]
                if i_shaft not in shaft_color:
                    raise RuntimeError('Turbine connected to shaft that is not connected to compressor: %r' % arch_el)
                color, fill_color = shaft_color[i_shaft]

                shaft_x_start[i_shaft] = min(shaft_x_start.get(i_shaft, 999999), x)
                shaft_x_end[i_shaft] = max(shaft_x_end.get(i_shaft, 0), x+length)

                # Draw polygons
                elements.append((1, self._poly([
                    (x, -.5*current_height*flow_height_frac),  # Left upper corner
                    (x+length, -.5*end_height*flow_height_frac),  # Right upper corner
                    (x+length, .5*end_height*flow_height_frac),  # Right lower corner
                    (x, .5*current_height*flow_height_frac),  # Left lower corner
                ], fill_color=fill_color, stroke_color=color, stroke_width=inner_stroke_width, closed=True)))
                elements.append((1, self._poly([
                    (x, -.5*current_height),  # Left upper corner
                    (x+length, -.5*end_height),  # Right upper corner
                    (x+length, .5*end_height),  # Right lower corner
                    (x, .5*current_height),  # Left lower corner
                ], stroke_color=color, stroke_width=stroke_width, closed=True)))

                outer_coords += [(x+length, .5*end_height)]

                total_height = max(total_height, end_height)
                current_height = end_height
                total_width += length
                x += length

            elif isinstance(arch_el, Nozzle):
                # total_width += stroke_width
                # x += stroke_width
                end_height = current_height*nozzle_ratio

                # Draw polygons
                elements.append((1, self._poly([
                    (x, -.5*current_height*flow_height_frac),  # Left upper corner
                    (x+nozzle_length, -.5*end_height*flow_height_frac*nozzle_ratio),  # Right upper corner
                    (x+nozzle_length, .5*end_height*flow_height_frac*nozzle_ratio),  # Right lower corner
                    (x, .5*current_height*flow_height_frac),  # Left lower corner
                ], fill_color=nozzle_color, stroke_color=nozzle_color, stroke_width=inner_stroke_width, closed=True)))
                elements.append((1, self._poly([
                    (x, -.5*current_height),  # Left upper corner
                    (x+nozzle_length, -.5*end_height),  # Right upper corner
                    (x+nozzle_length, .5*end_height),  # Right lower corner
                    (x, .5*current_height),  # Left lower corner
                ], stroke_color=nozzle_color, stroke_width=stroke_width, closed=True)))

                outer_coords += [(x+nozzle_length, .5*end_height)]

                total_height = max(total_height, end_height)
                current_height = end_height
                total_width += nozzle_length
                x += nozzle_length

                if arch_el.target is None:
                    break

            elif isinstance(arch_el, (Bleed, Duct)):
                pass

            else:
                raise RuntimeError('Unexpected element in core: %r' % arch_el)

            arch_el = arch_el.target

        # Draw the shafts
        y = .5*shaft_height
        for i_shaft, x1 in sorted(shaft_x_start.items(), key=lambda k: k[1]):
            if i_shaft not in shaft_x_start:
                continue

            x1 += .5*stroke_width
            x2 = shaft_x_end[i_shaft]-.5*stroke_width

            color = shaft_color[i_shaft][0]
            elements.append((2, self._line(x1, y, x2, y, stroke_color=color, stroke_width=shaft_height)))
            if y != 0:
                elements.append((2, self._line(x1, -y, x2, -y, stroke_color=color, stroke_width=shaft_height)))

            y_inner = y-.5*shaft_height
            if y_inner != 0:
                elements.append((3, self._line(x1, y_inner, x2, y_inner, stroke_color='black', stroke_width=.2)))
                elements.append((3, self._line(x1, -y_inner, x2, -y_inner, stroke_color='black', stroke_width=.2)))

            y += shaft_height

        # Draw outer line
        for n in [1, -1]:
            elements.append((3, self._path(
                [('M' if i == 0 else 'L')+('%s,%s' % (x, n*y)) for i, (x, y) in enumerate(outer_coords)],
                stroke_color='black', stroke_width=stroke_width, **{'stroke-linecap': 'square'})))

        group = E.g(*[el for _, el in sorted(elements, key=lambda e: e[0])])
        return group, total_width*1.02, total_height*1.1

    def _get_core_start(self, architecture: TurbofanArchitecture) -> Compressor:
        inlets = architecture.get_elements_by_type(Inlet)
        if len(inlets) != 1:
            raise RuntimeError('Inlet not found or multiple inlets found!')
        inlet: Inlet = inlets[0]

        start = inlet
        while True:
            if isinstance(start, (Inlet, Compressor, Duct)):
                compressor = inlet.target
            elif isinstance(start, Splitter):
                compressor = start.target_core
            else:
                raise RuntimeError('Unknown element when searching the start of the core: %r' % start)

            if compressor is None:
                raise RuntimeError('No more elements (searching start of core)!')

            if isinstance(compressor, Compressor):
                if self._is_fan(compressor):
                    continue
                return compressor

    @staticmethod
    def _is_fan(compressor: Compressor) -> bool:
        """Simple logic for detecting whether a compressor is a fan or part of the core compressors"""
        name = compressor.name.lower()
        return 'fan' in name or 'crtf' in name

    @property
    def line_height_px(self):
        return self._font_size*self._pt_to_px

    def _text(self, text, x=0., y=0., direction=0, rotation_deg: float = 0., **attr):
        # https://developer.mozilla.org/en-US/docs/Web/SVG/Tutorial/Texts
        text_kwargs = {
            'text-anchor': 'middle' if direction == 0 else ('start' if direction > 0 else 'end'),
            **attr,
        }

        group = E.g(
            E.text(text, **text_kwargs),
            transform='translate(%f, %f)' % (x, y+.3*self.line_height_px),
        )
        if rotation_deg != 0.:
            return self._rotate(group, rotation_deg, x, y)
        return group

    @classmethod
    def _rotate(cls, el: etree.Element, deg: float, x0: float = 0., y0: float = 0.):  # Positive is clockwise
        # https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/transform#rotate
        return cls._transform(el, 'rotate(%s,%s,%s)' % (deg, x0, y0))

    @classmethod
    def _translate(cls, el: etree.Element, dx: float, dy: float):
        # https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/transform#translate
        return cls._transform(el, 'translate(%s,%s)' % (dx, dy))

    @staticmethod
    def _transform(el: etree.Element, transform: str):
        # https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/transform
        return E.g(el, transform=transform)

    @staticmethod
    def _line(x1, y1, x2, y2, stroke_color: str, stroke_width: float = 1., **attr):
        # https://developer.mozilla.org/en-US/docs/Web/SVG/Tutorial/Basic_Shapes#line
        kwargs = {
            'stroke': stroke_color,
            'stroke-width': str(stroke_width),
            **attr,
        }
        return E.line(x1=str(x1), y1=str(y1), x2=str(x2), y2=str(y2), **kwargs)

    @staticmethod
    def _rect(x, y, width, height, fill_color: str, opacity: float = 1., stroke_color: str = None,
              stroke_width: float = 1., **attr):
        # https://developer.mozilla.org/en-US/docs/Web/SVG/Tutorial/Basic_Shapes#rectangles
        kwargs = {
            'fill': fill_color,
            'opacity': str(opacity),
        }
        if stroke_color is not None:
            kwargs['stroke'] = stroke_color
            kwargs['stroke-width'] = str(stroke_width)
        kwargs.update(attr)
        return E.rect(x=str(x), y=str(y), width=str(width), height=str(height), **kwargs)

    @staticmethod
    def _poly(coords: List[Tuple[float, float]], fill_color: str = 'transparent', opacity: float = 1.,
              stroke_color: str = 'black', stroke_width: float = 1., closed=False, **attr):
        # Open: https://developer.mozilla.org/en-US/docs/Web/SVG/Tutorial/Basic_Shapes#polyline
        # Closed: https://developer.mozilla.org/en-US/docs/Web/SVG/Tutorial/Basic_Shapes#polygon
        kwargs = {
            'points': ' '.join(['%s,%s' % (x, y) for x, y in coords]),
            'opacity': str(opacity),
        }
        if closed:
            kwargs['fill'] = fill_color
        if stroke_color is not None:
            kwargs['stroke'] = stroke_color
            kwargs['stroke-width'] = str(stroke_width)
        kwargs.update(attr)
        return E.polygon(**kwargs) if closed else E.polyline(**kwargs)

    @staticmethod
    def _path(instructions: List[str], fill_color: str = None, opacity: float = 1.,
              stroke_color: str = 'black', stroke_width: float = 1., **attr):
        # https://developer.mozilla.org/en-US/docs/Web/SVG/Tutorial/Paths
        kwargs = {
            'd': ' '.join(instructions),
            'opacity': str(opacity),
            'fill': fill_color or 'transparent',
        }
        if stroke_color is not None:
            kwargs['stroke'] = stroke_color
            kwargs['stroke-width'] = str(stroke_width)
        kwargs.update(attr)
        return E.path(**kwargs)

    def _define_linear_gradient(self, gradient_id: str, stops: List[Tuple[float, str, dict]],
                                direction_deg: float = 0.):
        """Stops are defined as tuple(fraction, color, attributes). Positive direction is clockwise."""
        # https://developer.mozilla.org/en-US/docs/Web/SVG/Tutorial/Gradients

        stop_els = [E.stop(offset='%s%%' % (frac*100,), **{'stop-color': color, **attr}) for frac, color, attr in stops]

        kwargs = {
            'id': gradient_id,
        }
        if direction_deg != 0:
            kwargs['x1'] = '0'
            kwargs['y1'] = '0'
            kwargs['x2'] = str(math.cos(math.radians(direction_deg)))
            kwargs['y2'] = str(math.sin(math.radians(direction_deg)))

        self._def_elements.append(E.linearGradient(*stop_els, **kwargs))

    def _get_root_el(self) -> etree.Element:

        # Should look like <svg xmlns="http://www.w3.org/2000/svg", ...>
        ns_url = 'http://www.w3.org/2000/svg'
        return E.svg(
            xmlns=ns_url,
            **{
                'font-family': '%s, serif' % self._font,
                'font-size': '%dpt' % self._font_size,
                'font-weight': 'light',
            }
        )


if __name__ == '__main__':
    from open_turb_arch.architecting.turbojet_architecture import get_turbojet_architecture

    arch = get_turbojet_architecture()
    ArchitectureVisualizer().export_svg(arch, 'turbojet1.svg')

    # inlet = Inlet(name='inlet')
    # inlet.target = compressor = Compressor(name='compressor')
    # compressor.target = hp_compressor = Compressor(name='hp_compressor')
    # hp_compressor.target = burner = Burner(name='burner')
    # burner.target = hp_turbine = Turbine(name='hp_turbine')
    # hp_turbine.target = turbine = Turbine(name='turbine')
    # turbine.target = nozzle = Nozzle(name='nozzle')
    # shaft = Shaft(name='shaft', rpm_design=1000, connections=[compressor, turbine])
    # shaft2 = Shaft(name='hp_shaft', rpm_design=2000, connections=[hp_compressor, hp_turbine])
    # arch = TurbofanArchitecture(elements=[
    #     inlet, compressor, hp_compressor, burner, hp_turbine, turbine, nozzle, shaft, shaft2])
    # ArchitectureVisualizer().export_svg(arch, 'turbojet2.svg')
