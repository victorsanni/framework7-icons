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

from existing_map import mapped_codepoints

SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
BLANK_PATH = os.path.join(SCRIPT_PATH, 'blank.svg')
INPUT_SVG_DIR = os.path.join(SCRIPT_PATH, '..', 'src')
OUTPUT_FONT_DIR = os.path.join(SCRIPT_PATH, '..', 'fonts')
MANIFEST_PATH = os.path.join(SCRIPT_PATH, 'manifest.json')
AUTO_WIDTH = True

def createGlyph(name, codepoint, file):
  glyph = f.createChar(codepoint, name)

  if not name in build_data['icons']:
    build_data['icons'][name] = [codepoint]
  else:
    build_data['icons'][name].append(codepoint)
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

# Import base characters
blank_glyph = f.createChar(-1, "BLANK")
blank_glyph.importOutlines(BLANK_PATH)
blank_glyph.width = 0
blank_glyph.altuni = [ord(c) for c in "0123456789abcdefghijklmnopqrstuvwzxyz_- "]

manifest_file = open(MANIFEST_PATH, 'r')
manifest_data = json.loads(manifest_file.read())
manifest_file.close()

build_data = copy.deepcopy(manifest_data)
build_data['icons'] = collections.OrderedDict()

font_name = manifest_data['name']

# Start at this codepoint since it's the last manually used codepoint from
# cupertino_icons 0.1.3.
codepoint = 0xf4d4

for dirname, dirnames, filenames in os.walk(INPUT_SVG_DIR):
  for filename in sorted(filenames):
    name, ext = os.path.splitext(filename)
    filePath = os.path.join(dirname, filename)
    size = os.path.getsize(filePath)
    if ext in ['.svg', '.eps']:

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

      if (name in mapped_codepoints[0]):
        mapped_value = mapped_codepoints[0][name]
        if isinstance(mapped_value, int):
          createGlyph(name, mapped_codepoints[0][name], filePath)
        else:
          for repeated_codepoint in mapped_codepoints[0][name]:
            createGlyph(name, repeated_codepoint, filePath)
        mapped_codepoints[0].pop(name)
      else:
        createGlyph(name, codepoint, filePath)
        codepoint += 1

      # if we created a temporary file, let's clean it up
      os.unlink(tmpsvgfile.name)

    # resize glyphs if autowidth is enabled
    if AUTO_WIDTH:
      f.autoWidth(0, 0, 512)

  fontfile = '%s/CupertinoIcons' % (OUTPUT_FONT_DIR)

f.fontname = font_name
f.familyname = font_name
f.fullname = font_name
f.generate(fontfile + '.ttf')

scriptPath = os.path.dirname(os.path.realpath(__file__))

# Hint the TTF file
subprocess.call('ttfautohint -s -f -n ' + fontfile + '.ttf ' + fontfile + '-hinted.ttf > /dev/null 2>&1 && mv ' + fontfile + '-hinted.ttf ' + fontfile + '.ttf', shell=True)

manifest_data['icons'] = collections.OrderedDict(sorted(build_data['icons'].items(), key=lambda glyph: glyph[0]))

print("Save Manifest, Icons: %s" % ( len(manifest_data['icons']) ))
print(f"Unused mappings {mapped_codepoints}")
f = open(MANIFEST_PATH, 'w')
f.write( json.dumps(manifest_data, indent=2, separators=(',', ': ')) )
f.close()
