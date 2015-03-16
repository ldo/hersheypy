"""Drawing text in Cairo using Hershey fonts.
These are vector fonts that must be stroked, not filled, so they cannot
be represented directly in a common font format like TrueType. But
they can be rendered using the user-font facility of the Cairo graphics API.

On Debian, the Hershey fonts come from the hershey-fonts-data package,
and can be found in /usr/share/hershey-fonts when that package is installed.

This module requires my Qahirah wrapper for Cairo <https://github.com/ldo/qahirah>.
"""

import qahirah as qah
from qahirah import \
    CAIRO, \
    Glyph, \
    Vector

debug = False

class HersheyGlyphs :
    "container for decoded data from a Hershey font file. glyphs is a mapping from glyph" \
    " codes to HersheyGlyphs.Glyph objects."

    __slots__ = ("glyphs", "baseline_y", "min", "max", "scale")

    class Glyph :
        "information about a single glyph. min_x and max_x are the minimum and maximum" \
        " horizontal extents, and path is a tuple of path segments, each consisting of" \
        " a set of qahirah.Vector points to be joined by straight lines."

        __slots__ = ("parent", "min_x", "max_x", "path")

        def __init__(self, parent, min_x, max_x, path) :
            self.parent = parent
            self.min_x = min_x
            self.max_x = max_x
            self.path = path
        #end __init__

    #end Glyph

    def __init__(self, filename, align_left = True) :
        self.glyphs = {}
        self.baseline_y = 9
        min_x = max_x = min_y = max_y = 0
        linenr = 0
        for line in open(filename, "r") :
            linenr += 1
            glyphnr = int(line[:5].strip())
            if glyphnr == 12345 :
                glyphnr = linenr + 31
            #end if
            nr_points = int(line[5:8].strip())
            pathsegs = []
            points = None
            i = 0
            x_extents = None
            while True :
                if i == nr_points :
                    xc = None
                else :
                    xc = line[8 + i * 2]
                    yc = line[8 + i * 2 + 1]
                    if xc + yc == " R" :
                        xc = None
                    #end if
                #end if
                if xc == None : # pen up
                    assert x_extents != None
                    if points != None :
                        pathsegs.append(points)
                    #end if
                    points = None
                #end if
                if i == nr_points :
                    break
                if points == None :
                    points = []
                #end if
                if xc != None :
                    coords = (ord(xc) - ord("R"), ord(yc) - ord("R"))
                    min_x = min(min_x, coords[0])
                    max_x = max(max_x, coords[0])
                    min_y = min(min_y, coords[1])
                    max_y = max(max_y, coords[1])
                    if x_extents == None :
                        x_extents = coords
                    else :
                        coords = Vector.from_tuple(coords)
                        if align_left :
                            coords -= Vector(x_extents[0], 0)
                        #end if
                        points.append(coords)
                    #end if
                #end if
                i += 1
            #end while
            if align_left :
                x_extents = (0, x_extents[1] - x_extents[0])
            #end if
            self.glyphs[glyphnr] = HersheyGlyphs.Glyph(self, x_extents[0], x_extents[1], pathsegs)
        #end for
        self.min = Vector(min_x, min_y)
        self.max = Vector(max_x, max_y)
        if align_left :
            self.max -= Vector(self.min.x, 0)
            self.min = Vector(0, self.min.y)
        #end if
        width = max_x - min_x
        height = max_y - min_y
        self.scale = 1 / max(width, height)
    #end __init__

    def __len__(self) :
        return \
            len(self.glyphs)
    #end __len__

    def __getitem__(self, item) :
        return \
            self.glyphs[item]
    #end __getitem__

    def keys(self) :
        return \
            self.glyphs.keys()
    #end keys

#end HersheyGlyphs

def make(glyphs, line_width, line_spacing = 1.0, kern = False) :
    "constructs a qahirah.UserFontFace object from the specified HersheyGlyphs" \
    " object. line_width is the width of lines for stroking, relative to font" \
    " coordinates (e.g. 0.01 is a reasonable value), and line_spacing is the" \
    " relative spacing between text lines."

    def init_hershey(scaled_font, ctx, font_extents) :
        "UserFontFace init callback to define the font_extents."
        font_extents.ascent = (glyphs.baseline_y - glyphs.min.y) * glyphs.scale
        font_extents.descent = (glyphs.max.y - glyphs.baseline_y) * glyphs.scale
        font_extents.height = line_spacing
        font_extents.max_x_advance = (glyphs.max.x - glyphs.min.x) * glyphs.scale
        # font_extents.max_y_advance = 0
        return \
            CAIRO.STATUS_SUCCESS
    #end init_hershey

    def render_hershey_glyph(scaled_font, glyph, ctx, text_extents) :
        "UserFontFace render callback to actually render a glyph and define its text_extents."
        glyph_entry = glyphs.glyphs.get(glyph)
        if glyph_entry != None :
            for pathseg in glyph_entry.path :
                ctx.new_sub_path()
                for point in pathseg :
                    ctx.line_to((point - Vector(0, glyphs.baseline_y)) * glyphs.scale)
                #end for
            #end for
            ctx.set_line_width(the_font.user_data["hershey_line_width"])
            ctx.stroke()
            text_extents.x_bearing = glyph_entry.min_x * glyphs.scale
            text_extents.x_advance = (glyph_entry.max_x - glyph_entry.min_x) * glyphs.scale
            if debug :
                # indicate location of baseline and glyph origin and horizontal bounds
                baseline_y = 0
                ctx.move_to(Vector(glyph_entry.min_x, - 4 + baseline_y) * glyphs.scale)
                ctx.line_to(Vector(glyph_entry.min_x, baseline_y) * glyphs.scale)
                ctx.line_to(Vector(glyph_entry.max_x, baseline_y) * glyphs.scale)
                ctx.line_to(Vector(glyph_entry.max_x, - 4 + baseline_y) * glyphs.scale)
                ctx.move_to(Vector(0, 4 + baseline_y) * glyphs.scale)
                ctx.line_to(Vector(0, baseline_y) * glyphs.scale)
                ctx.stroke()
            #end if
        #end if
        return \
            CAIRO.STATUS_SUCCESS
    #end render_hershey_glyph

    def unicode_to_glyph(scaled_font, unicode) :
        "UserFontFace character-code-to-glyph mapping callback."
        # dummy, just to test mapping callback actually works
        return \
            (CAIRO.STATUS_SUCCESS, unicode)
    #end unicode_to_glyph

    def text_to_glyphs(scaled_font, text, cluster_mapping) :
        "UserFontFace text-sequence-to-glyphs mapping callback."
        # I am using this to make the lines on the cursive Hershey font
        # join up correctly. I could arrange that more simply by setting
        # the left side bearing of all glyphs to 0, rather than preserving
        # the original x-coordinates, but this way I get to exercise the
        # text_to_glyphs functionality of qahirah.UserFontFace to ensure
        # it works!
        glyphs_list = []
        xpos = 0
        for ch in text :
            code = unicode_to_glyph(scaled_font, ord(ch))[1] # might as well use my own function
            entry = Glyph(code, Vector(xpos - glyphs[code].min_x, 0) * glyphs.scale)
            xpos += glyphs[code].max_x - glyphs[code].min_x
            glyphs_list.append(entry)
        #end for
        if cluster_mapping :
            cluster_result = (((1, 1),) * len(text), 0)
            # TODO: try effect of CAIRO.TEXT_CLUSTER_FLAG_BACKWARD
        else :
            cluster_result = ()
        #end if
        return \
            (CAIRO.STATUS_SUCCESS, glyphs_list) + cluster_result
    #end text_to_glyphs

#begin make
    the_font = qah.UserFontFace.create \
      (
        init_func = init_hershey,
        render_glyph_func = render_hershey_glyph,
      )
    if kern :
        the_font.text_to_glyphs_func = text_to_glyphs
    else :
        the_font.unicode_to_glyph_func = unicode_to_glyph
    #end if
    the_font.user_data["hershey_glyphs"] = glyphs # for caller's benefit
    the_font.user_data["hershey_line_width"] = line_width # so caller can adjust
    return \
        the_font
#end make

def load(filename, line_width, line_spacing = 1.0, align_left = True, kern = False) :
    "convenience wrapper which loads a HersheyGlyphs object from the specified file," \
    " and invokes make with it and the specified and line_spacing parameters."
    glyphs = HersheyGlyphs(filename, align_left)
    return \
        make(glyphs, line_width, line_spacing, kern)
#end load
