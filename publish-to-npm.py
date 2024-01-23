import argparse
import copy
import json
import os
import shutil
import stat
import subprocess

# Expect NPM_TOKEN as environment variable rather than argument to prevent the
# token from showing up in build logs

parser = argparse.ArgumentParser(
    prog="publish-to-npm",
    description="Publishes npm packages",
)

parser.add_argument("-w", "--windows-binary-source-location")
parser.add_argument("-d", "--darwin-binary-source-location")
parser.add_argument("-l", "--linux-binary-source-location")
parser.add_argument("-e", "--new-version")

args = parser.parse_args()

windows_binary_source_location = args.windows_binary_source_location
darwin_binary_source_location = args.darwin_binary_source_location
linux_binary_source_location = args.linux_binary_source_location
new_version = args.new_version

def rewrite_version_of_package_json(package_json, version):
    package_json_copy = copy.deepcopy(package_json)
    package_json_copy["version"] = version
    return package_json_copy


def rewrite_versions_of_optional_dependencies(package_json, version):
    package_json_copy = copy.deepcopy(package_json)
    package_json_copy["optionalDependencies"]["@zokka/zokka-binary-darwin_x64"] = version
    package_json_copy["optionalDependencies"]["@zokka/zokka-binary-linux_x64"] = version
    package_json_copy["optionalDependencies"]["@zokka/zokka-binary-win32_x64"] = version
    return package_json_copy


try:
    os.environ["NPM_TOKEN"]
except KeyError:
    raise Exception("The NPM_TOKEN environment variable must be set otherwise we cannot publish to npm!")

top_level_npm_directory = "./installers/npm/"
darwin_directory = "./installers/npm/packages/darwin_x64/"
windows_directory = "./installers/npm/packages/win32_x64/"
linux_directory = "./installers/npm/packages/linux_x64/"

def copy_and_chmod_file(source, destination):
    try:
        executable = destination
        shutil.copyfile(source, executable)
        current_stat = os.stat(executable)
        os.chmod(executable, current_stat.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    except shutil.SameFileError:
        print(f"Not copying {source} because location has not changed")
        pass

copy_and_chmod_file(darwin_binary_source_location, darwin_directory + "/zokka")
copy_and_chmod_file(windows_binary_source_location, windows_directory + "/zokka.exe")
copy_and_chmod_file(linux_binary_source_location, linux_directory + "/zokka")

for directory in [darwin_directory, windows_directory, linux_directory]:
    with open(directory + "package.json", "r+") as f:
        package_json = json.load(f)
        new_package_json = rewrite_version_of_package_json(package_json, new_version)
        f.seek(0)
        json.dump(new_package_json, f, indent=2)
        f.truncate()
    if "alpha" in new_version:
        subprocess.run(["npm", "publish", "--tag", "alpha"], cwd=directory)
    elif "beta" in new_version:
        subprocess.run(["npm", "publish", "--tag", "beta"], cwd=directory)
    else:
        subprocess.run(["npm", "publish"], cwd=directory)


with open(top_level_npm_directory + "package.json", "r+") as f:
    package_metadata = json.load(f)
    new_package_metadata = \
        rewrite_version_of_package_json(rewrite_versions_of_optional_dependencies(package_metadata, new_version), new_version)
    f.seek(0)
    json.dump(new_package_metadata, f, indent=2)
    f.truncate()

if "alpha" in new_version:
    subprocess.run(["npm", "publish", "--tag", "alpha"], cwd=top_level_npm_directory)
    # Apparently npm doesn't allow multiple flags at once with publish, so
    # we need to manually add latest with npm-dist-tag
    subprocess.run(["npm", "dist-tag", "add", f"zokka@{new_version}", "latest"], cwd=top_level_npm_directory)
elif "beta" in new_version:
    subprocess.run(["npm", "publish", "--tag", "beta"], cwd=top_level_npm_directory)
    subprocess.run(["npm", "dist-tag", "add", f"zokka@{new_version}", "latest"], cwd=top_level_npm_directory)
else:
    subprocess.run(["npm", "publish"], cwd=top_level_npm_directory)
