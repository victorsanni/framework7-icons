# Font generation script from Ionicons + FontCustom
# https://github.com/FontCustom/fontcustom/
# https://github.com/driftyco/ionicons/
# http://fontcustom.com/
# http://ionicons.com/

import fontforge
import os
import subprocess
import tempfile
import json
import copy
import collections

from existing_map import mapped_codepoints, aliases

SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
INPUT_SVG_DIR = os.path.join(SCRIPT_PATH, '..', 'src')
OUTPUT_FONT_DIR = os.path.join(SCRIPT_PATH, '..', 'fonts')
MANIFEST_PATH = os.path.join(SCRIPT_PATH, 'manifest.json')
AUTO_WIDTH = True

def getOrCreateLigatureComponentFor(char):
  glyph = f.createChar(ord(char))
  glyph.width = 0
  return glyph.glyphname

def createGlyph(name, codepoints, file):
  assert len(codepoints) == len(set(codepoints))
  assert len(codepoints) != 0
  codepoint, *tail = codepoints
  glyph = f.createChar(codepoint, name)
  assert not glyph.changed, ("Glyph %s is already assigned. Check for duplicated SVGs.") % glyph
  if tail:
    glyph.altuni = tail

  assert name not in build_data['icons']
  build_data['icons'][name] = codepoints
  glyph.addPosSub('ligacomp', [getOrCreateLigatureComponentFor(c) for c in name])
  for alias in aliases.pop(name, []):
    assert alias != name
    assert alias
    build_data['icons'][alias] = codepoints
    glyph.addPosSub('ligacomp', [getOrCreateLigatureComponentFor(c) for c in alias])

  glyph.importOutlines(file)
  # set glyph size explicitly or automatically depending on autowidth
  if AUTO_WIDTH:
    glyph.left_side_bearing = glyph.right_side_bearing = 0
    glyph.round()
  else:
    if name in ['chevron_back', 'chevron_forward']:
      # These are special since they're not square shaped. Squish them more.
      glyph.width = 224
    # There are legacy font glyphs from different svg sources. Leave them as is.
    else:
      glyph.width = 512
  return glyph

unusable_names = {
  # Keywords in Dart we can't use as names.
  'return': 'return_icon',
}

f = fontforge.font()
f.encoding = 'UnicodeFull'
f.design_size = 28
f.em = 512
f.ascent = 448
f.descent = 64

# Add lookup table
f.addLookup("ligatable","gsub_ligature",None,(("liga",(("latn",("dflt")),)),))
f.addLookupSubtable("ligatable","ligacomp")

manifest_file = open(MANIFEST_PATH, 'r')
manifest_data = json.loads(manifest_file.read())
manifest_file.close()

build_data = copy.deepcopy(manifest_data)
build_data['icons'] = collections.OrderedDict()

font_name = manifest_data['name']

# Start at this codepoint since it's the last manually used codepoint from
# cupertino_icons 0.1.3.
last_new_codepoint = 0xf4d3

for dirname, dirnames, filenames in os.walk(INPUT_SVG_DIR):
  for filename in sorted(filenames):
    name, ext = os.path.splitext(filename)
    filePath = os.path.join(dirname, filename)
    size = os.path.getsize(filePath)
    if ext not in ['.svg', '.eps']:
      continue
    # hack removal of <switch> </switch> tags
    svgfile = open(filePath, 'r+')
    tmpsvgfile = tempfile.NamedTemporaryFile(suffix=ext, delete=False, mode='w')
    svgtext = svgfile.read()
    svgfile.seek(0)

    # replace the <switch> </switch> tags with 'nothing'
    svgtext = svgtext.replace('<switch>', '')
    svgtext = svgtext.replace('</switch>', '')

    tmpsvgfile.file.write(svgtext)

    svgfile.close()
    tmpsvgfile.file.close()

    filePath = tmpsvgfile.name
    # end hack

    if (name in unusable_names):
      name = unusable_names[name]

    mapped_value = mapped_codepoints.pop(name, None)
    codepoints = [(last_new_codepoint:=last_new_codepoint + 1)] if mapped_value is None else mapped_value
    glyph = createGlyph(name, codepoints, filePath);

    # if we created a temporary file, let's clean it up
    os.unlink(tmpsvgfile.name)


# resize glyphs if autowidth is enabled
if AUTO_WIDTH:
  f.autoWidth(0, 0, 512)

fontfile = '%s/CupertinoIcons' % (OUTPUT_FONT_DIR)

f.fontname = font_name
f.familyname = font_name
f.fullname = font_name
f.version = "1.08"
f.copyright = ""
# Generate the ttf without the glyphnames in the post table to reduce size
f.generate(fontfile + '.ttf', flags=('opentype','short-post'))

scriptPath = os.path.dirname(os.path.realpath(__file__))

# Hint the TTF file
subprocess.call('ttfautohint -s -f -n ' + fontfile + '.ttf ' + fontfile + '-hinted.ttf > /dev/null 2>&1 && mv ' + fontfile + '-hinted.ttf ' + fontfile + '.ttf', shell=True)

manifest_data['icons'] = collections.OrderedDict(sorted(build_data['icons'].items(), key=lambda glyph: glyph[0]))

print("Save Manifest, Icons: %s" % ( len(manifest_data['icons']) ))
if mapped_codepoints:
  print(f"Unused mappings {mapped_codepoints}")
if aliases:
  print(f"Unused aliases {aliases}")
f = open(MANIFEST_PATH, 'w')
f.write( json.dumps(manifest_data, indent=2, separators=(',', ': ')) )
f.close()
