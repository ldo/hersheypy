"""Drawing text in Cairo using Hershey fonts.
These are vector fonts that must be stroked, not filled, so they cannot
be represented directly in a common font format like TrueType. But
they can be rendered using the user-font facility of the Cairo graphics API.

On Debian, the Hershey fonts come from the hershey-fonts-data package,
and can be found in /usr/share/hershey-fonts when that package is installed.

This module requires my Qahirah wrapper for Cairo <https://github.com/ldo/qahirah>.
"""
#+
# Copyright 2015 by Lawrence D'Oliveiro <ldo@geek-central.gen.nz>.
# Licensed under CC-BY <http://creativecommons.org/licenses/by/4.0/>.
#-

import os
import qahirah as qah
from qahirah import \
    CAIRO, \
    Glyph, \
    Vector

debug = False

class HersheyGlyphs :
    "container for decoded data from a Hershey font file. glyphs is a mapping from glyph" \
    " codes to HersheyGlyphs.Glyph objects, while encoding, if not None, provides a mapping" \
    " from Unicode character codes to glyph numbers. If encoding is None, then glyph numbers" \
    " can be directly interpreted as ASCII character codes."

    __slots__ = ("glyphs", "baseline_y", "encoding", "min", "max", "scale")

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
        basename = os.path.splitext(os.path.basename(filename))[0]
        self.encoding = self.encodings.get(basename)
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

    def make_encodings() :
        # make ASCII encodings for fonts with non-ASCII glyph numbers
        # “Understanding is compression.” -- Gregory Chaitin
        syms1 = \
            { # always in the same place, sometimes subsetted
                "\\" : 804,
                "_" : 999,
                "[" : 2223,
                "]" : 2224,
                "{" : 2225,
                "}" : 2226,
                "|" : 2229, # or U+007C?
                "<" : 2241,
                ">" : 2242,
                "~" : 2246,
                "↑" : 2262, # non-ASCII
                "^" : 2262, # ASCII alternative to above
                "%" : 2271,
                "@" : 2273,
                "#" : 2275,
            }
        syms2 = \
            { # these sometimes moved/subsetted
                "." : 3710,
                "," : 3711,
                ":" : 3712,
                ";" : 3713,
                "!" : 3714,
                "?" : 3715,
                "‘" : 3716, # non-ASCII
                "’" : 3717, # non-ASCII
                # "'" : 3717, # should I offer ASCII alternative to above?
                "&" : 3718,
                "$" : 3719,
                "/" : 3720,
                "(" : 3721,
                ")" : 3722,
                "*" : 3723,
                "-" : 3724,
                "+" : 3725,
                "=" : 3726,
                "\"" : 3728,
                "°" : 3729, # non-ASCII
            }

        redirects = \
            {
                "cyrilc_1" : {}, # filled in below
                "cyrillic" :
                    {
                        36 : 0x42b,
                        37 : 0x446,
                        38 : 0x44b,
                        65 : 0x410,
                        66 : 0x411,
                        67 : 0x42d,
                        68 : 0x414,
                        69 : 0x418,
                        70 : 0x424,
                        71 : 0x413,
                        72 : 0x416,
                        73 : 0x419, # actually looks like 0x418
                        74 : 0x427,
                        75 : 0x41a,
                        76 : 0x41b,
                        77 : 0x41c,
                        78 : 0x41d,
                        79 : 0x41e,
                        80 : 0x41f,
                        81 : 0x428,
                        82 : 0x420,
                        83 : 0x421,
                        84 : 0x422,
                        85 : 0x42e,
                        86 : 0x412,
                        87 : 0x429,
                        88 : 0x425,
                        89 : 0x423,
                        90 : 0x417,
                        91 : 0x415,
                        93 : 0x42a,
                        94 : 0x42f,
                        95 : 0x42c,
                        96 : 0x426,
                        101 : 0x439,
                    },
                "greeka" :
                    {
                        65 : 0x391,
                        66 : 0x392,
                        67 : 0x3a7,
                        68 : 0x394,
                        69 : 0x395,
                        70 : 0x3a6,
                        71 : 0x393,
                        72 : 0x397,
                        73 : 0x399,
                        74 : None,
                        75 : 0x39a,
                        76 : 0x39b,
                        77 : 0x39c,
                        78 : 0x39d,
                        79 : 0x39f,
                        80 : 0x3a0,
                        81 : 0x398,
                        82 : 0x3a1,
                        83 : 0x3a3,
                        84 : 0x3a4,
                        85 : 0x3a5,
                        86 : None,
                        87 : 0x3a9,
                        88 : 0x39e,
                        89 : 0x3a8,
                        90 : 0x396,
                        106 : None,
                        118 : None,
                    },
                "greeks" : {}, # filled in below
            }
        for ch in range(0, 26) :
            redirects["cyrilc_1"][ch + ord("A")] = ch + 0x410
            redirects["cyrilc_1"][ch + ord("a")] = ch + 0x430
        #end for
        for ch in range(65, 92) :
            if ch != 69 and ch != 73 :
                redirects["cyrillic"][ch + 32] = redirects["cyrillic"][ch] + 32
            #end if
        #end for
        for ch in range(93, 96) :
            redirects["cyrillic"][ch + 31] = redirects["cyrillic"][ch] + 32
        #end for
        for ch in range(0, 26) :
            if ch != 9 and ch != 21 :
                redirects["greeka"][ch + 65 + 32] = redirects["greeka"][ch + 65] + 32
            #end if
        #end for
        for ch in range(0, 17) :
            redirects["greeks"][ch + 65] = ch + 0x391
            redirects["greeks"][ch + 97] = ch + 0x3b1
        #end for
        for ch in range(17, 24) :
            redirects["greeks"][ch + 65] = ch + 0x392
            redirects["greeks"][ch + 97] = ch + 0x3b2
        #end for
        greek_extra = \
            {
                chr(0x00b7) : 74, # middle dot, or is it 0x2022 bullet?
                "°" : 86,
                "×" : 106,
                "÷" : 118,
            }

        def make_enc(preset = None, uc = None, lc = None, digits = None, space = None, sym1_except = None, sym2 = 3710, sym2_except = None, nr_letters = 26, extra = None, redirect = None) :
            # makes an encoding given starting points for common glyph ranges
            # plus various optional exceptions
            enc = {}
            if preset == "ascii" :
                for k in range(32, 128) :
                    enc[k] = k
                #end for
            else :
                if preset == "rowmans" :
                    digits = 700
                    sym1_except = {"#", "|"}
                    sym2 = 710
                    sym2_except = {"‘", "’", "&", "*", "\"", "°"}
                    extra = \
                        {
                            "\"" : 717,
                            "°" : 718,
                            "|" : 723, # or U+007C?
                            "‘" : 730,
                            "’" : 731,
                            "#" : 733,
                            "&" : 734,
                            "*" : 2219,
                        }
                elif preset == "greekc" :
                    digits = 2200
                    sym2 = 2210
                    sym2_except = {"‘", "’", "&", "$", "*", "-", "+", "=", "\"", "°"}
                    extra = \
                        {
                            "‘" : 2252,
                            "’" : 2251,
                            "&" : 2272,
                            "$" : 2274,
                            "*" : 2219,
                            "-" : 2231,
                            "+" : 2232,
                            "=" : 2238,
                            "°" : 2218,
                        }
                #end if
                for k in syms1 :
                    if sym1_except == None or k not in sym1_except :
                        enc[ord(k)] = syms1[k]
                    #end if
                #end for
                for k in syms2 :
                    if sym2_except == None or k not in sym2_except :
                        enc[ord(k)] = syms2[k] - 3710 + sym2
                    #end if
                #end for
                for i in range(nr_letters) :
                    enc[ord("A") + i] = i + uc
                    enc[ord("a") + i] = i + lc
                #end for
                if space == None :
                    space = digits - 1
                #end if
                enc[ord(" ")] = space
                for i in range(10) :
                    enc[ord("0") + i] = digits + i
                #end for
            #end if
            if extra != None :
                for k in extra :
                    enc[ord(k)] = extra[k]
                #end for
            #end if
            if redirect != None :
                for k in redirect :
                    redir = redirect[k]
                    if redir != None :
                        enc[redir] = enc[k]
                    #end if
                #end for
                for k in redirect :
                    del enc[k]
                #end for
            #end if
            return \
                enc
        #end make_enc

        encodings = \
            { # key is basename of font file without .jhf extension
                "cyrilc_1" :
                    make_enc
                      (
                        preset = "greekc",
                        uc = 2801,
                        lc = 2901,
                        redirect = redirects["cyrilc_1"]
                      ),
                "cyrillic" : make_enc(preset = "ascii", redirect = redirects["cyrillic"]),
                "gothgbt" : make_enc(uc = 3501, lc = 3601, digits = 3700),
                "gothgrt" : make_enc(uc = 3301, lc = 3401, digits = 3700),
                "gothitt" : make_enc(uc = 3801, lc = 3901, digits = 3700),
                "greek" :
                    make_enc(preset = "ascii", extra = greek_extra, redirect = redirects["greeka"]),
                "greekc" :
                    make_enc
                      (
                        preset = "greekc",
                        uc = 2027,
                        lc = 2127,
                        nr_letters = 24,
                        redirect = redirects["greeks"]
                      ),
                "greeks" :
                    make_enc
                      (
                        preset = "rowmans",
                        uc = 527,
                        lc = 627,
                        nr_letters = 24,
                        redirect = redirects["greeks"]
                      ),
                "rowmand" : make_enc(uc = 2501, lc = 2601, digits = 2700, sym2 = 2710),
                "rowmans" : make_enc(preset = "rowmans", uc = 501, lc = 601),
                "rowmant" : make_enc(uc = 3001, lc = 3101, digits = 3200, sym2 = 3210),
                "scriptc" : make_enc(uc = 2551, lc = 2651, digits = 2750, sym2 = 2760),
                "scripts" :
                    make_enc
                      (
                        uc = 551,
                        lc = 651,
                        digits = 2750,
                        space = 699,
                        sym1_except = {"#", "|"},
                        sym2 = 2760,
                        sym2_except = {".", "-", "+", "=", "°"},
                        extra =
                            {
                                "." : 710,
                                "°" : 718,
                                "|" : 723, # or U+007C?
                                "-" : 724,
                                "+" : 725,
                                "=" : 726,
                                "#" : 733,
                            },
                      ),
                "timesg" :
                    make_enc(preset = "ascii", extra = greek_extra, redirect = redirects["greeka"]),
            }
        return \
            encodings
    #end make_encodings

    encodings = make_encodings()

    del make_encodings

#end HersheyGlyphs

def make(glyphs, line_width, line_spacing = 1.0, use_encoding = True, kern = False) :
    "constructs a qahirah.UserFontFace object from the specified HersheyGlyphs" \
    " object. line_width is the width of lines for stroking, relative to font" \
    " coordinates (e.g. 0.01 is a reasonable value), and line_spacing is the" \
    " relative spacing between text lines."

    if glyphs.encoding == None :
        use_encoding = False # no encoding to use
    #end if

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
        if use_encoding :
            glyph = glyphs.encoding.get(unicode, 0)
        else :
            glyph = unicode
        #end if
        return \
            (CAIRO.STATUS_SUCCESS, glyph)
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

def load(filename, line_width, line_spacing = 1.0, use_encoding = True, align_left = True, kern = False) :
    "convenience wrapper which loads a HersheyGlyphs object from the specified file," \
    " and invokes make with it and the specified and line_spacing parameters."
    glyphs = HersheyGlyphs(filename, align_left = align_left)
    return \
        make(glyphs, line_width, line_spacing, use_encoding = use_encoding, kern = kern)
#end load
