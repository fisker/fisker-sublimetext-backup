import sublime, sublime_plugin
import subprocess, shutil, traceback, os, json, shlex, collections

class create_new_projectCommand(sublime_plugin.WindowCommand):
  project_type = None

  def run(self, **kwargs):

    self.window.show_quick_panel(PROJECT_TYPE_SUPPORTED, self.project_type_selected)

  def project_type_selected(self, index):

    if index == -1:
      return
      
    self.project_type = PROJECT_TYPE_SUPPORTED[index]

    # Testing WindowView()
    # self.WindowView = WindowView()
    # self.WindowView.addTitle(text="Create JavaScript Project")
    # self.WindowView.add(text="\n")
    # self.WindowView.add(text="Project Path: ", region_id="test")
    # self.WindowView.addInput(value=os.path.expanduser("~")+os.path.sep, region_id="project_path")
    # self.WindowView.add(text="\n\n")
    # Hook.apply(self.project_type+"_create_window_view", self.WindowView)
    # self.WindowView.add(text="\n\n")
    # self.WindowView.addButton(text="CREATE", scope="javascriptenhancements.button_ok")
    # self.WindowView.add(text="        ")
    # self.WindowView.addButton(text="CANCEL", scope="javascriptenhancements.button_cancel")
    # self.WindowView.add(text=" \n")
    # self.WindowView.addEventListener("drag_select", "click.javascriptenhancements.button_ok", lambda view: self.project_path_on_done(self.WindowView.getInput("project_path")))
    # self.WindowView.addEventListener("drag_select", "click.javascriptenhancements.button_cancel", lambda view: self.WindowView.close())

    self.window.show_input_panel("Project Path:", os.path.expanduser("~")+os.path.sep, self.project_path_on_done, None, None)

  def project_path_on_done(self, path):

    path = path.strip()

    if os.path.isdir(os.path.join(path, PROJECT_SETTINGS_FOLDER_NAME)):
      sublime.error_message("Can't create the project. There is already another project in "+path+".")
      return

    if not os.path.isdir(path):
      if sublime.ok_cancel_dialog("The path \""+path+"\" doesn't exists.\n\nDo you want create it?", "Yes"):
        os.makedirs(path)
      else:
        return

    Hook.apply("create_new_project", path)
    Hook.apply(self.project_type+"_create_new_project", path)

    os.makedirs(os.path.join(path, PROJECT_SETTINGS_FOLDER_NAME))

    PROJECT_SETTINGS_FOLDER_PATH = os.path.join(path, PROJECT_SETTINGS_FOLDER_NAME)

    default_config = json.loads(open(os.path.join(PROJECT_FOLDER, "create_new_project", "default_config.json")).read(), object_pairs_hook=collections.OrderedDict)
    
    sublime_project_file_path = os.path.join(path, os.path.basename(path)+".sublime-project")
    package_json_file_path = os.path.join(path, "package.json")
    flowconfig_file_path = os.path.join(path, ".flowconfig")
    bookmarks_path = os.path.join(PROJECT_SETTINGS_FOLDER_PATH, "bookmarks.json")
    project_details_file = os.path.join(PROJECT_SETTINGS_FOLDER_PATH, "project_details.json")
    project_settings = os.path.join(PROJECT_SETTINGS_FOLDER_PATH, "project_settings.json")

    if not os.path.exists(sublime_project_file_path) :
      with open(sublime_project_file_path, 'w+', encoding="utf-8") as file:
        file.write(json.dumps(default_config["sublime_project"], indent=2))

    if ( self.project_type == "empty" or self.project_type == "cordova" ) and not os.path.exists(package_json_file_path) :
      with open(package_json_file_path, 'w+', encoding="utf-8") as file:
        file.write(json.dumps(default_config["package_json"], indent=2))

    with open(bookmarks_path, 'w+', encoding="utf-8") as file:
      file.write(json.dumps(default_config["bookmarks"], indent=2))
    with open(project_details_file, 'w+', encoding="utf-8") as file:
      file.write(json.dumps(default_config["project_details"], indent=2))
    with open(project_settings, 'w+', encoding="utf-8") as file:
      file.write(json.dumps(default_config["project_settings"], indent=2))

    if not os.path.exists(flowconfig_file_path) :
      node = NodeJS(check_local=True)
      result = node.execute("flow", ["init"], is_from_bin=True, chdir=path)
      if not result[0]:
        sublime.error_message("Can't initialize flow.")
      else:
        with open(flowconfig_file_path, 'r+', encoding="utf-8") as file:
          content = file.read()
          content = content.replace("[ignore]", """[ignore]
<PROJECT_ROOT>/"""+PROJECT_SETTINGS_FOLDER_NAME+"""/.*""")
          file.seek(0)
          file.truncate()
          file.write(content)

    Hook.apply(self.project_type+"_after_create_new_project", path, "create_new_project")
    Hook.apply("after_create_new_project", path, "create_new_project")

    if self.project_type == "empty":
      open_project_folder(get_project_settings(path)["project_file_name"])

class add_javascript_project_typeCommand(sublime_plugin.WindowCommand):
  project_type = None
  settings = None

  def run(self, **kwargs):
    self.settings = get_project_settings()
    if self.settings:
      self.window.show_quick_panel(PROJECT_TYPE_SUPPORTED, self.project_type_selected)
    else:
      sublime.error_message("No JavaScript project found.")

  def project_type_selected(self, index):

    if index == -1:
      return

    self.project_type = PROJECT_TYPE_SUPPORTED[index]
    self.window.show_input_panel("Working Directory:", self.settings["project_dir_name"]+os.path.sep, self.working_directory_on_done, None, None)

  def working_directory_on_done(self, working_directory):

    working_directory = shlex.quote( working_directory.strip() )

    if not os.path.isdir(working_directory):
      os.makedirs(working_directory)

    Hook.apply("add_javascript_project_type", working_directory, "add_project_type")
    Hook.apply(self.project_type+"_add_javascript_project_type", working_directory, "add_project_type")

  def is_visible(self):
    return is_javascript_project()

  def is_enabled(self):
    return is_javascript_project()

class add_javascript_project_type_configurationCommand(sublime_plugin.WindowCommand):
  project_type = None
  settings = None

  def run(self, *args):
    self.settings = get_project_settings()
    if self.settings:
      self.window.show_quick_panel(list( set(PROJECT_TYPE_SUPPORTED) - set(["yeoman"]) ), self.project_type_selected)
    else:
      sublime.error_message("No JavaScript project found.")

  def project_type_selected(self, index):

    if index == -1:
      return

    self.project_type = list( set(PROJECT_TYPE_SUPPORTED) - set(["yeoman"]) )[index]
    self.window.show_input_panel("Working directory:", self.settings["project_dir_name"]+os.path.sep, self.working_directory_on_done, None, None)

  def working_directory_on_done(self, working_directory):

    working_directory = shlex.quote( working_directory.strip() )

    if not os.path.isdir(working_directory):
      os.makedirs(working_directory)

    Hook.apply("add_javascript_project_configuration", working_directory, "add_project_configuration")
    Hook.apply(self.project_type+"_add_javascript_project_configuration", working_directory, "add_project_configuration")

  def is_visible(self):
    return is_javascript_project()

  def is_enabled(self):
    return is_javascript_project()
