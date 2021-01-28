"""Generate the menu items."""
import configparser
import json
import os
import sys
from pathlib import Path
import re
from typing import Text
import xml.etree.ElementTree as et
from xml.dom import minidom
import shutil
import logging
import distutils.dir_util


def write_directory_file(name, file_dir, icon_dir):
    logging.info(f"Adding submenu for '{name}'")
    file_path = file_dir/f"vnm-{name.lower().replace(' ', '-')}.directory"
    icon_path = icon_dir/f"{name.lower().split()[0]}.png"
    icon_src = (Path(__file__).parent/'icons'/icon_path.name)
    # breakpoint()
    try:
        shutil.copy2(icon_src, icon_path)
    except FileNotFoundError:
        logging.warning(f'{icon_src} not found')
        icon_src = (Path(__file__).parent/'icons/vnm.png')
        shutil.copy2(icon_src, icon_path)

    # Generate `.directory` file
    entry = configparser.ConfigParser()
    entry.optionxform = str
    entry["Desktop Entry"] = {
        "Name": name,
        "Comment": name,
        "Icon": icon_path,
        "Type": "Directory",
    }
    file_dir.mkdir(exist_ok=True)
    with open(Path(file_path), "w",) as directory_file:
        entry.write(directory_file, space_around_delimiters=False)
    return file_path


def add_menu(installdir: Path, name: Text, category: Text) -> None:
    """Add a submenu to 'VNM' menu.

    Parameters
    ----------
    name : Text
        The name of the submenu.
    """

    # Generate `.directory` file
    file_dir = installdir/"desktop-directories/apps"
    icon_dir = installdir/f"icons"
    file_path = write_directory_file(name, file_dir, icon_dir)

    # Add entry to `.menu` file
    menu_path = installdir/"vnm-applications.menu"
    with open(menu_path, "r") as xml_file:
        s = xml_file.read()
    s = re.sub(r"\s+(?=<)", "", s)
    root = et.fromstring(s)
    category_name = f'vnm-{category.lower().replace(" ", "-")}'
    for menu_el in root.findall(".//Menu/Menu"):
        if menu_el[2][0][0].text == category_name:
        # menu_el = root.findall("./Menu/Menu")[0]
            sub_el = et.SubElement(menu_el, "Menu")
            name_el = et.SubElement(sub_el, "Name")
            name_el.text = name.capitalize()
            dir_el = et.SubElement(sub_el, "Directory")
            dir_el.text = f'vnm/apps/{file_path.name}'
            include_el = et.SubElement(sub_el, "Include")
            and_el = et.SubElement(include_el, "And")
            cat_el = et.SubElement(and_el, "Category")
            cat_el.text = name.replace(" ", "-")
            cat_el.text = f"vnm-{cat_el.text}"
            xmlstr = minidom.parseString(et.tostring(root)).toprettyxml(indent="\t")
            with open(menu_path, "w") as f:
                f.write('<!DOCTYPE Menu PUBLIC "-//freedesktop//DTD Menu 1.0//EN"\n ')
                f.write('"http://www.freedesktop.org/standards/menu-spec/1.0/menu.dtd">\n\n')
                f.write(xmlstr[xmlstr.find("?>") + 3 :])
            os.chmod(menu_path, 0o644)
            break


class VNMApp:
    def __init__(
        self,
        deskenv: Text,
        installdir: Path,
        sh_prefix: Text,
        name: Text,
        version: Text,
        category: Text,
        exec: Text = "",
        terminal: bool = True
        ):
        """Add an application to the menu.

        Parameters
        ----------
        name : Text
            The name of the application.
        version : Text
            The version of the applciation.
        exec : Text
            The command to run when clicking on the application item.
        category : Text
            The category defining the menu in which the application must be added.
        terminal : bool
            If set to ``True``, a terminal is opened when launching the application.
        """
        self.deskenv = deskenv
        self.installdir = installdir
        self.sh_prefix = sh_prefix
        self.name = name
        self.version= version
        self.category = category
        self.exec = exec #TODO change exec to safer variable name
        self.terminal = terminal

    def app_names(self):
        self.basename = f"vnm-{self.name.lower().replace(' ', '-').replace('.', '_')}"
        self.category = f"vnm-{self.category}"
        if self.exec:
            # assumes that executable name is before the dash and after the dash the normal container name and version
            self.container_name = self.name.split("-")[1]
            self.exec_name = self.name.split("-")[0] + " " + self.name.split("-")[1].split(" ")[1]
        else: 
            self.container_name = self.name
            self.exec_name = self.name

    def add_app_sh(self):
        fetch_and_run_sh = self.installdir/"fetch_and_run.sh"
        self.bin_path = self.installdir/"bin"
        self.bin_path.mkdir(exist_ok=True)
        self.sh_path = self.bin_path/f"{self.basename}.sh"
        with open(self.sh_path, "w",) as self.sh_file:
            self.sh_file.write("#!/usr/bin/env bash\n")
            self.sh_file.write(f"{self.sh_prefix} ")
            if self.deskenv == 'mate':
                self.sh_file.write(f"{str(fetch_and_run_sh)} {self.container_name} {self.version} {self.exec}")
            else:
                self.sh_file.write(f"{str(fetch_and_run_sh)} {self.container_name} {self.version} {self.exec}")
            self.sh_file.write('\n')
        os.chmod(self.sh_path, 0o755)

    def add_app_menu(self) -> None:
        icon_path = self.installdir/f"icons/{self.name.split()[0]}.png"
        icon_src = Path(__file__).parent/'icons'/icon_path.name
        try:
            shutil.copy2(icon_src, icon_path)
        except FileNotFoundError:
            logging.warning(f'{icon_src} not found')
            icon_src = (Path(__file__).parent/'icons/vnm.png')
            shutil.copy2(icon_src, icon_path)
        entry = configparser.ConfigParser()
        entry.optionxform = str

        if self.deskenv == 'mate':
            entry["Desktop Entry"] = {
                "Name": self.exec_name,
                "GenericName": self.exec_name,
                "Comment": self.name + " " + self.version,
                "Exec": f"mate-terminal --window --title \"{self.name}\" -e \'/bin/bash {str(self.sh_path)}\'",
                "Icon": icon_path,
                "Type": "Application",
                "Categories": self.category
            }
        else:
            entry["Desktop Entry"] = {
                "Name": self.exec_name,
                "GenericName": self.exec_name,
                "Comment": self.name + " " + self.version,
                "Exec": str(self.sh_path),
                "Icon": icon_path,
                "Type": "Application",
                "Categories": self.category,
                "Terminal": str(self.terminal).lower()
            }

        applications_path = self.installdir/"applications"
        applications_path.mkdir(exist_ok=True)
        desktop_path = applications_path/f"{self.basename}.desktop"

        with open(desktop_path, "w",) as desktop_file:
            entry.write(desktop_file, space_around_delimiters=False)
        os.chmod(desktop_path, 0o644)


def apps_from_json(cli, deskenv: Text, installdir: Path, appsjson: Path, sh_prefix='')  -> None:
    # Read applications file
    with open(appsjson, "r") as json_file:
        menu_entries = json.load(json_file)

    for menu_name, menu_data in menu_entries.items():
        # Add submenu
        if not cli:
            add_menu(installdir, menu_name, 'all applications')
            for category in menu_data.get("categories") or []:
                add_menu(installdir, menu_name, category)
        for app_name, app_data in menu_data.get("apps", {}).items():
            app = VNMApp(
                deskenv=deskenv,
                installdir=installdir,
                sh_prefix=sh_prefix,
                name=app_name,
                category=menu_name.replace(" ", "-"),
                **app_data)
            app.app_names()
            app.add_app_sh()
            if not cli:
                app.add_app_menu()


def vnm_xml(xml: Path, newxml: Path) -> None:
    oldtag = '<Menu>'
    newtag = '<MergeFile>vnm-applications.menu</MergeFile>'
    tagcount = 0
    replace = True
    
    with open(xml, "r") as fh:
        lines = fh.readlines()
        for line in lines:
            if newtag in line:
                replace = False
                break

    with open(newxml, "w") as fh:
        for line in lines:
            if replace and oldtag in line:
                tagcount += 1
                if tagcount == 2:
                    fh.write(re.sub(f'{oldtag}', f'{newtag}\n\t{oldtag}', line))
                else:
                    fh.write(line)
            else:
                fh.write(line)
    try:
        et.parse(newxml)
    except et.ParseError:
        logging.error(f'InvalidXMLError with appmenu [{newxml}]')
        logging.error('Exiting ...')
        sys.exit()


def build_menu(installdir, deskenv, sh_prefix):
    climode = False
    if deskenv == 'cli':
        climode = True

    shutil.copy2('neurodesk/vnm-applications.menu.template', installdir/'vnm-applications.menu')
    shutil.copy2('neurodesk/fetch_and_run.sh', installdir)
    shutil.copy2('neurodesk/fetch_containers.sh', installdir)
    shutil.copy2('neurodesk/configparser.sh', installdir)
    shutil.copy2('config.ini', installdir)
    distutils.dir_util.copy_tree('neurodesk/transparent-singularity', str(installdir/'transparent-singularity'))
    os.chmod(installdir/'fetch_and_run.sh', 0o755)
    os.chmod(installdir/'fetch_containers.sh', 0o755)
    os.chmod(installdir/'configparser.sh', 0o755)

    if not climode:
        # add_vnm_menu(installdir, 'VNM Neuroimaging')
        directories_path = installdir/"desktop-directories"
        icon_dir = installdir/"icons"
        write_directory_file("VNM Neuroimaging", directories_path, icon_dir)
        write_directory_file("All Applications", directories_path, icon_dir)
        write_directory_file("Functional Imaging", directories_path, icon_dir)
        write_directory_file("Data Organisation", directories_path, icon_dir)
        write_directory_file("Diffusion Imaging", directories_path, icon_dir)
        write_directory_file("Structural Imaging", directories_path, icon_dir)
        write_directory_file("Quantitative Imaging", directories_path, icon_dir)
        write_directory_file("Image Segmentation", directories_path, icon_dir)
        write_directory_file("Image Registration", directories_path, icon_dir)
        write_directory_file("Programming", directories_path, icon_dir)

    appsjson = Path('neurodesk/apps.json').resolve(strict=True)
    (installdir/'icons').mkdir(exist_ok=True)
    apps_from_json(climode, deskenv, installdir, appsjson, sh_prefix)

    # Remove any symlinks from local appdir
    # Prevents symlink recursion
    vnm_appdir = installdir/'applications'
    for file in vnm_appdir.glob('*'):
        if file.is_symlink():
            os.unlink(file)
