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
import io
import qahirah as qah
from qahirah import \
    CAIRO, \
    Glyph, \
    Matrix, \
    Vector

debug = False

default_path = os.getenv("HERSHEY_FONTS_DIR", "/usr/share/hershey-fonts")
  # where the fonts are to be found, default is location on Debian
default_ext = ".jhf"

class HersheyGlyphs :
    "container for decoded data from a Hershey font file. glyphs is a mapping from glyph" \
    " codes to HersheyGlyphs.Glyph objects, while encoding, if not None, provides a mapping" \
    " from Unicode character codes to glyph numbers. If encoding is None, then glyph numbers" \
    " can be directly interpreted as ASCII character codes. Do not instantiate directly;" \
    " use the load method instead."

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

        def draw(self, ctx, matrix = Matrix.identity()) :
            "draws the path into ctx, which is a qahirah.Context, transformed" \
            " through matrix, which is a qahirah.Matrix."
            glyphs = self.parent
            matrix = matrix * Matrix.scale(glyphs.scale)
            for pathseg in self.path :
                ctx.new_sub_path()
                for point in pathseg :
                    ctx.line_to(matrix.map((point - Vector(0, glyphs.baseline_y))))
                #end for
            #end for
        #end draw

    #end Glyph

    @staticmethod
    def load(filename, align_left = True, use_encoding = True) :
        "creates a new HersheyGlyphs object by decoding the contents of the" \
        " specified .jhf file."
        if filename.find("/") < 0 :
            if filename.find(".") < 0 :
                filename += default_ext
            #end if
            filename = os.path.join(default_path, filename)
        #end if
        result = HersheyGlyphs()
        result.glyphs = {}
        result.baseline_y = 9
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
            result.glyphs[glyphnr] = HersheyGlyphs.Glyph(result, x_extents[0], x_extents[1], pathsegs)
        #end for
        result.min = Vector(min_x, min_y)
        result.max = Vector(max_x, max_y)
        if align_left :
            result.max -= Vector(result.min.x, 0)
            result.min = Vector(0, result.min.y)
        #end if
        width = max_x - min_x
        height = max_y - min_y
        result.scale = 1 / max(width, height)
        basename = os.path.splitext(os.path.basename(filename))[0]
        if use_encoding :
            result.encoding = result.encodings.get(basename)
        else :
            result.encoding = None
        #end if
        return \
            result
    #end load

    def save(self, tofile, use_encoding = True) :
        "uses tofile.write() to output this HersheyGlyphs object in .jhf file format."
        if self.encoding == None :
            use_encoding = False
        #end if
        if use_encoding :
            codes = self.encoding.keys()
        else :
            codes = self.glyphs.keys()
        #end if
        for code in sorted(codes) :
            assert code > 0 and code <= 99999 # i.e. it fits in 5 digits
            if use_encoding :
                glyph = self.glyphs[self.encoding[code]]
            else :
                glyph = self.glyphs[code]
            #end if
            tofile.write("%5d" % code)
            if len(glyph.path) != 0 :
                nr_points = sum(len(p) for p in glyph.path) + len(glyph.path)
            else :
                nr_points = 1
            #end if
            assert nr_points < 1000 # i.e. it fits in 3 digits
            tofile.write \
              (
                    "%3d%c%c"
                %
                    (
                        nr_points,
                        chr(glyph.min_x + ord("R")),
                        chr(glyph.max_x + ord("R")),
                    )
              )
            for i, pathseg in enumerate(glyph.path) :
                if i != 0 :
                    tofile.write(" R") # pen up
                #end if
                for p in pathseg :
                    tofile.write \
                      (
                            "%c%c"
                        %
                            (
                                chr(p.x + ord("R")),
                                chr(p.y + ord("R")),
                            )
                      )
                #end for
            #end for
            tofile.write("\n")
        #end for
    #end save

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

    def __or__(f1, f2) :
        "forms the union of two HersheyGlyphs objects."
        result = HersheyGlyphs()
        assert (f1.encoding != None) == (f2.encoding != None), "cannot have partially-encoded font"
        f2_offset = max(f1.glyphs)
        f2_remap = None
        if f1.encoding == None :
            result.encoding = None
        else :
            result.encoding = dict(f1.encoding)
            f2_remap = {}
            for k in sorted(f2.encoding) :
                if k not in result.encoding :
                    code = f2.encoding[k]
                    if code in f1.glyphs :
                        f2_offset += 1
                        f2_remap[code] = f2_offset
                        result.encoding[k] = f2_offset
                    else :
                        result.encoding[k] = code
                    #end if
                #end if
            #end for
        #end if
        result.glyphs = dict(f1.glyphs)
        for k in f2.glyphs :
            glyph = f2.glyphs[k]
            if f2_remap != None :
                code = f2_remap.get(k, k)
            else :
                f2_offset += 1
                code = f2_offset
            #end if
            result.glyphs[code] = HersheyGlyphs.Glyph(result, glyph.min_x, glyph.max_x, glyph.path)
        #end for
        result.baseline_y = f1.baseline_y
        result.min = Vector(min(f1.min.x, f2.min.x), min(f1.min.y, f2.min.y))
        result.max = Vector(max(f1.max.x, f2.max.x), max(f1.max.y, f2.max.y))
        dims = result.max - result.min
        result.scale = 1 / max(dims.x, dims.y)
        return \
            result
    #end __or__

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
                        105 : 0x438,
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
                "math" :
                    {
                        33 : 0x00b1, # plus-minus sign
                        34 : 0x2213, # minus-or-plus sign
                        35 : 0x00d7, # multiplication sign
                        36 : 0x00b7, # middle dot or 0x22c5 dot operator?
                        38 : 0x2264, # less-than or equal to
                        39 : 0x2265, # greater-than or equal to
                        58 : 0x220f, # n-ary product
                        59 : 0x2211, # n-ary summation
                        63 : 0x2260, # not equal to
                        64 : 0x2261, # identical to
                        94 : 0x221d, # proportional to
                        95 : 0x221e, # infinity
                        96 : 0x00b0, # degree sign
                        99 : 0x221a, # square root
                        100 : 0x2282, # subset of
                        101 : 0x222a, # union
                        102 : 0x2283, # superset of
                        103 : 0x2229, # intersection
                        104 : 0x2208, # element of
                        105 : 0x2192, # rightwards arrow
                        106 : 0x2191, # upwards arrow
                        107 : 0x2190, # leftwards arrow
                        108 : 0x2193, # downwards arrow
                        109 : 0x2202, # partial differential
                        110 : 0x2207, # nabla
                        111 : None, # same as 99
                        113 : 0x222b, # integral
                        118 : 0x2203, # there exists
                        119 : 0x2135, # alef symbol
                        120 : 0x00f7, # division sign
                        121 : 0x2225, # parallel
                        122 : 0x22a5, # up tack
                        124 : 0x2220, # angle
                        126 : 0x2234, # therefore
                      # no good match for these, put in private-use area:
                        98 : 0xe041, # (smaller) square root
                        112 : 0xe04f, # (smaller) integral
                        114 : 0xe051, # (large) left parenthesis
                        115 : 0xe052, # (large) right parenthesis
                        116 : 0xe053, # (large) left square bracket
                        117 : 0xe054, # (large) right square bracket
                    },
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
        fix_tilde = {127 : 126}

        def make_enc(preset = None, uc = None, lc = None, digits = None, space = None, sym1_except = None, sym2 = 3710, sym2_except = None, nr_letters = 26, extra = None, redirect = None, redirect2 = None, redirect3 = None) :
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
            for r in redirect, redirect2, redirect3 :
                if r != None :
                    for k in r :
                        redir = r[k]
                        if redir != None :
                            enc[redir] = enc[k]
                        #end if
                    #end for
                    for k in r :
                        del enc[k]
                    #end for
                #end if
            #end if
            return \
                enc
        #end make_enc

        encodings = \
            { # key is basename of font file without .jhf extension
                "astrology" :
                    make_enc
                      (
                        preset = "ascii",
                        redirect =
                            {
                              # best approximations I could find
                                33 : 0x2653, # pisces
                                35 : 0x2609, # sun
                                36 : 0x263F, # mercury
                                37 : 0x2640, # female sign
                                38 : 0x2295, # circled plus
                                39 : 0x2642, # male sign
                                42 : 0x2643, # jupiter
                                43 : 0x2644, # saturn
                                45 : 0x26e2, # astronomical symbol for uranus
                                47 : 0x2646, # neptune
                                58 : 0x2647, # pluto
                                59 : 0x263e, # last quarter moon (?)
                                60 : 0x2604, # comet
                                61 : 0x2605, # black star (?)
                                62 : 0x260a, # ascending node
                                63 : 0x260b, # descending node
                                64 : 0x2648, # aries
                                91 : 0x2649, # taurus
                                93 : 0x264a, # gemini
                                94 : 0x264b, # cancer
                                95 : 0x264c, # leo
                                96 : 0x264d, # virgo
                                123 : 0x264f, # scorpius
                                124 : 0x2650, # sagittarius
                                125 : 0x2651, # capricorn (?)
                                126 : 0x2652, # aquarius
                            },
                        redirect2 =
                            {
                                127 : 126, # tilde
                            },
                      ),
                # "cursive" : ASCII
                "cyrilc_1" :
                    make_enc
                      (
                        preset = "greekc",
                        uc = 2801,
                        lc = 2901,
                        redirect = redirects["cyrilc_1"]
                      ),
                "cyrillic" : make_enc(preset = "ascii", redirect = redirects["cyrillic"], redirect2 = fix_tilde),
                # "futural" : ASCII
                # "futuram" : ASCII
                "gothgbt" : make_enc(uc = 3501, lc = 3601, digits = 3700),
                "gothgrt" : make_enc(uc = 3301, lc = 3401, digits = 3700),
                # "gothiceng" : ASCII
                # "gothicger" : ASCII
                # "gothicita" : ASCII
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
                "markers" :
                    {
                        32 : 32,
                        0x25ef : 65, # large circle, or 0x25cb white circle
                        0x2b1c : 66, # white large square, or 0x25a1 white square
                        0x25be : 67, # white up-pointing triangle
                        0x25ca : 68, # lozenge, or perhaps 0x2b28 white medium lozenge
                        0x2606 : 69, # white star
                        ord("+") : 71,
                        ord("×") : 72,
                        ord("*") : 73,
                        0x25cf : 74, # black circle
                        0x25a0 : 75, # black square
                        0x25be : 76, # black up-pointing triangle
                        0x25c0 : 77, # black left-pointing triangle
                        0x25bc : 78, # black down-pointing triangle
                        0x25b6 : 79, # black right-pointing triangle
                        0x26d8 : 80, # heavy white down-pointing triangle
                      # no good match for these, put in private-use area:
                        0xe000 : 70, # like white plus sign
                      # rest are either blank or duplicates
                    },
                "mathlow" :
                    make_enc
                      (
                        preset = "ascii",
                        redirect = redirects["math"],
                        redirect2 =
                            {
                                97 : 36, # dollar sign
                                127 : 126, # tilde
                            },
                        redirect3 = dict
                          (
                            (c, c + 32) for c in range(65, 91)
                          ),
                      ),
                "mathupp" :
                    make_enc
                      (
                        preset = "ascii",
                        redirect = dict
                          (
                                (
                                    (97, None), # duplicate of 42 asterisk
                                    (123, None), # duplicate of 93 right square bracket (right curly bracket is missing)
                                )
                            +
                                tuple((k, d[k]) for d in (redirects["math"],) for k in d)
                          ),
                        redirect2 =
                            {
                                125 : 123, # left curly bracket
                                127 : 126, # tilde
                            }
                      ),
                "meteorology" :
                    make_enc
                      (
                        preset = "ascii",
                        redirect =
                            {
                              # best approximations I could find
                                34 : 0x02609, # sun
                                35 : 0x0204e, # low asterisk
                                36 : 0x025b2, # black up-pointing triangle
                                38 : 0x02bca, # top half black circle
                                39 : 0x02503, # black lower left triangle
                                40 : 0x02303, # up arrowhead
                                95 : 0x0221e, # infinity
                                124 : 0x02608, # thunderstorm
                                126 : 0x1f300, # cyclone
                              # give up on rest, stick them in private use area
                              # leave gaps if I change my mind about above assignments
                                33 : 0x0e000, # looks like comma
                                41 : 0x0e007, # 0x02312, # arc
                                43 : 0x0e008, # 0x025e0, # upper half circle
                                58 : 0x0e009, # 0x025e1, # lower half circle (actually small, like 41)
                                59 : 0x0e00a, # looks like lower-pointing quadrant
                                60 : 0x0e00b, # looks like right-pointing semicircle
                                61 : 0x0e00c, # 0x025de, # lower right quadrant circular arc
                                62 : 0x0e00d, # 0x025df, # lower left quadrant circular arc
                                94 : 0x0e00e, # looks exactly like letter S
                                96 : 0x0e010, # looks like backward letter S on its side
                            },
                        redirect2 = fix_tilde,
                      ),
                "music" :
                    make_enc
                      (
                        preset = "ascii",
                        redirect =
                            { # some of these are guesses
                                34 : 0x1d19f, # musical symbol ornament stroke-5
                                35 : 0x1d19e, # musical symbol ornament stroke-4
                                36 : 0x1d157, # musical symbol void notehead
                                37 : None, # same as 36
                                38 : 0x1d158, # musical symbol notehead black
                                39 : 0x0266F, # music sharp sign
                                40 : 0x0266e, # music natural sign
                                41 : 0x0266d, # music flat sign
                                45 : 0x1d13e, # musical symbol eighth rest
                                46 : 0x1d13d, # musical symbol quarter rest
                                59 : 0x1d11e, # musical symbol g clef
                                60 : None, # same as 47
                                61 : 0x1d122, # musical symbol f clef
                                63 : 0x1d121, # musical symbol c clef
                                64 : None, # same as 43
                                94 : 0x02019, # right single quotation mark
                                96 : 0x02018, # left single quotatin mark
                              # give up on following, put in private-use area
                                42 : 0x0e008,
                                43 : 0x0e009,
                                44 : 0x0e00a,
                                47 : 0x0e00d, # musical symbol f clef (old form)
                                62 : 0x0e01c, # looks like old-form c clef
                            },
                        redirect2 =
                            {
                                95 : 45, # looks more like hyphen than underscore
                            },
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
                # "timesi" : ASCII
                # "timesib" : ASCII
                "timesg" :
                    make_enc(preset = "ascii", extra = greek_extra, redirect = redirects["greeka"]),
                # "timesr" : ASCII
                # "timesrb" : ASCII
            }
        return \
            encodings
    #end make_encodings

    encodings = make_encodings()

    del make_encodings

#end HersheyGlyphs

def make(glyphs, line_width, line_spacing = 1.0, use_encoding = True, kern = False, line_dash = None, line_cap = None) :
    "constructs a qahirah.UserFontFace object from the specified HersheyGlyphs" \
    " object. line_width is the width of lines for stroking, relative to font" \
    " coordinates (e.g. 0.01 is a reasonable value), line_spacing is the" \
    " relative spacing between text lines, use_encoding indicates whether to use a" \
    " Unicode-compatible encoding if available, kern whether to do kerning, and line_dash" \
    " and line_cap specify dash and cap settings for drawing the lines."

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
            glyph_entry.draw(ctx)
            # no point trying to allow user to change line_width, line_dash and line_cap
            # settings via user_data in the FontFace or the ScaledFont, since Cairo
            # caches this information and does not currently provide a way to flush that cache.
            ctx.set_line_width(line_width)
            if line_dash != None :
                ctx.set_dash(line_dash)
            #end if
            if line_cap != None :
                ctx.set_line_cap(line_cap)
            #end if
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
            if unicode in glyphs.glyphs :
                glyph = unicode
            else :
                glyph = 0
            #end if
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
    if isinstance(glyphs, tuple) or isinstance(glyphs, list) :
        merged = glyphs[0]
        for g in glyphs[1:] :
            merged |= g
        #end for
        glyphs = merged
    #end if
    if glyphs.encoding == None :
        use_encoding = False # no encoding to use
    #end if
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
    return \
        the_font
#end make

def load(filename, line_width, line_spacing = 1.0, use_encoding = True, align_left = True, kern = False, line_dash = None, line_cap = None) :
    "convenience wrapper which loads a HersheyGlyphs object from the specified file," \
    " and invokes make with it and the specified and line_spacing parameters."
    if isinstance(filename, tuple) or isinstance(filename, list) :
        glyphs = tuple(HersheyGlyphs.load(f, align_left = align_left, use_encoding = use_encoding) for f in filename)
    else :
        glyphs = HersheyGlyphs.load(filename, align_left = align_left, use_encoding = use_encoding)
    #end if
    return \
        make(glyphs, line_width, line_spacing, use_encoding = use_encoding, kern = kern, line_dash = line_dash, line_cap = line_cap)
#end load
