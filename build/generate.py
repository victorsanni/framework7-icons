# Font generation script from Ionicons
# https://github.com/driftyco/ionicons/
# http://ionicons.com/

from subprocess import call
import os
import json

from existing_map import old_names


BUILDER_PATH = os.path.dirname(os.path.abspath(__file__))
ROOT_PATH = os.path.join(BUILDER_PATH, '..')
FONTS_FOLDER_PATH = os.path.join(ROOT_PATH, 'fonts')

def main():
  generate_font_files()

  data = get_manifest()

  generate_dart_file(data)

  generate_cheatsheet(data)

def generate_font_files():
  print("Generate Fonts")
  cmd = "fontforge -script %s/generate_font.py" % (BUILDER_PATH)
  call(cmd, shell=True)


def generate_cheatsheet(data):
  print("Generate Cheatsheet")

  cheatsheet_file_path = os.path.join(ROOT_PATH, 'cheatsheet/index.html')
  template_path = os.path.join(BUILDER_PATH, 'cheatsheet', 'template.html')
  icon_row_path = os.path.join(BUILDER_PATH, 'cheatsheet', 'icon-row.html')

  f = open(template_path, 'r')
  template_html = f.read()
  f.close()

  f = open(icon_row_path, 'r')
  icon_row_template = f.read()
  f.close()

  content = []

  for name in data['icons'].keys():
    item_row = icon_row_template

    item_row = item_row.replace('{{name}}', name)

    content.append(item_row)

  template_html = template_html.replace("{{font_name}}", data["name"])
  # template_html = template_html.replace("{{font_version}}", package["version"])
  template_html = template_html.replace("{{icon_count}}", str(len(data["icons"])) )
  template_html = template_html.replace("{{content}}", '\n'.join(content) )

  f = open(cheatsheet_file_path, 'w')
  f.write(template_html)
  f.close()

def get_manifest():
  manifest_path = os.path.join(BUILDER_PATH, 'manifest.json')
  f = open(manifest_path, 'r')
  data = json.loads(f.read())
  f.close()
  return data

def generate_dart_file(data):
  output = []
  skipped = []
  data = data['icons']
  for name, codepoints in data.items():
    if name not in old_names.keys():
      output.append(f"  /// <i class='cupertino-icons md-36'>{name}</i> cupertino icon for {name}. Available on cupertino_icons package 1.0.0+ only.")
      output.append("\n")
      if codepoints[0] in old_names.values():
        for old_name, old_codepoint in old_names.items():
          if old_codepoint in codepoints:
            output.append(f"  /// This is the same icon as [{old_name}] which is available in cupertino_icons 0.1.3.")
            output.append("\n")
      output.append(f"  static const IconData {name} = IconData({hex(codepoints[0])}, fontFamily: iconFont, fontPackage: iconFontPackage);")
      output.append("\n")
    else:
      skipped.append(name)
  f = open(os.path.join(BUILDER_PATH, 'cupertino_generated_icons.dart'), 'w')
  f.write(''.join(output))

  flutter_root = os.environ['FLUTTER_ROOT']
  cupertino_icons_file = open(os.path.join(flutter_root, 'packages', 'flutter', 'lib', 'src', 'cupertino', 'icons.dart'), 'r')
  cupertino_icons = cupertino_icons_file.readlines()
  cupertino_icons_file.close()

  new_cupertino_icons = []
  generating = False
  for line in cupertino_icons:
    if "END GENERATED" in line:
      generating = False
    if not generating:
      new_cupertino_icons.append(line)
    if "BEGIN GENERATED" in line:
      generating = True
      new_cupertino_icons.extend(output)

  cupertino_icons_file = open(os.path.join(flutter_root, 'packages', 'flutter', 'lib', 'src', 'cupertino', 'icons.dart'), 'w')
  cupertino_icons_file.write(''.join(new_cupertino_icons))
  cupertino_icons_file.close()
  print(f'Skipped {skipped} overlapping glyphs with existing definitions')

  # Print instructions for old manual dartdocs
  # for old_name, old_codepoint in old_names.items():
  #   for glyph in data['icons']:
  #     if glyph['codepoint'] == old_codepoint:
  #       if not old_name in skipped:
  #         print(f'-- {old_name} -- ')
  #         print(f"This is the same icon as [{glyph['name']}] in cupertino_icons 1.0.0+.")

if __name__ == "__main__":
  main()
