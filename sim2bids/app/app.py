import json
import os
import shutil
from collections import OrderedDict

import panel as pn
import pylems_py2xml
import pylems_py2xml as py2xml

# import local packages
import sim2bids.utils
from sim2bids.generate import structure, subjects
from sim2bids.preprocess import preprocess as prep
from sim2bids.convert import convert
from sim2bids.templates import templates as temp
from sim2bids.app import utils


# define global variables
SID = None
DESC = 'default'                            # short description that identifies input data
OUTPUT = os.path.join('..', 'output')       # output folder to store appersions
CENTRES = False                             # whether centres.txt|nodes.txt|labels.txt were found
MULTI_INPUT = False                         # whether input files include single- or multi-subjects
ALL_FILES = None                            # list of all file paths (gets supplemented in subjects.py)
CODE = None                                 # path to python code if exists
H5_CONTENT = dict()
MODEL_NAME = None

# define all accepted files
ACCEPTED = ['weight', 'distance', 'tract_length', 'delay', 'speed',                 # Network (net)
            'nodes', 'labels', 'centres', 'area', 'hemisphere', 'cortical',         # Coordinates (coord)
            'orientation', 'average_orientation', 'normal', 'times', 'vertices',    # Coordinates (coord)
            'faces', 'vnormal', 'fnormal', 'sensor', 'map', 'volume',               # Coordinates (coord)
            'cartesian2d', 'cartesian3d', 'polar2d', 'polar3d',                     # Coordinates (coord)
            'vars', 'stimuli', 'noise', 'spike', 'raster', 'ts', 'event', 'emp'     # Timeseries (ts)
            'fc']                                                                   # Spatial (spatial)

TO_EXTRACT = ['weights.txt', 'centres.txt', 'distances.txt',                        # folder "net"
              'areas.txt', 'average_orientations.txt', 'cortical.txt',              # folder "coord"
              'hemisphere.txt', 'normals.txt'                                       # folder "coord"
              ]

# define accepted extensions
ACCEPTED_EXT = ['txt', 'csv', 'dat', 'h5', 'mat', 'zip', 'py']


def main(path: str, files: list, subs: dict = None, save: bool = False, layout: bool = False):
    """Main brain function that creates subjects, auto-generated structure,
    and saves apperted files.

    Parameters
    ----------
    path :
        param files:
    subs :
        param save:
    layout :
        return:
    path: str :

    files: list :

    subs: dict :
         (Default value = None)
    save: bool :
         (Default value = False)
    layout: bool :
         (Default value = False)

    Returns
    -------

    """
    global MODEL_NAME

    # whether to generate layout
    if layout:
        # if no subjects are passed, define them
        if subs is None:
            subs = subjects.Files(path, files).subs

    # only save conversions if 'save' is True
    if save and subs is not None:
        # save conversions
        save_output(subs)

        # save code
        if CODE is not None:
            save_code()

    if H5_CONTENT is not None and 'model' in H5_CONTENT.keys():
        pylems_py2xml.main.XML(inp=H5_CONTENT, output_path=os.path.join(OUTPUT, 'param'),
                               uid=H5_CONTENT['model'], app=True, suffix=DESC)
        MODEL_NAME = utils.get_model()
        transfer_xml()

    # finally, remove all empty folders
    remove_empty()

    # return subjects and possible layouts only if it's enabled
    if layout:
        return subs, structure.create_layout(subs)

    # otherwise, return None
    return None, None


def save_output(subs):
    """

    Parameters
    ----------
    subs :
        return:

    Returns
    -------

    """

    # create the folder that will store conversions
    if not os.path.exists(OUTPUT):
        os.mkdir(OUTPUT)

    # prepare the output folder
    check_output_folder()

    # verify folders exist
    structure.check_folders(OUTPUT)

    def save(sub, ses=None):
        """

        Parameters
        ----------
        sub :

        ses :
             (Default value = None)

        Returns
        -------

        """
        name = None

        for k, v in sub.items():
            # create folders according to session and subject count types
            folders = create_sub_struct(OUTPUT, v, ses_name=ses)
            k_lower = k.lower()

            if 'weight' in k_lower or 'distance' in k_lower:
                name = 'wd'
            elif 'centre' in k_lower:
                name = 'centres'
            elif 'node' in k_lower or 'label' in k_lower:
                name = 'coord'
            elif 'fc' in k_lower:
                name = 'spatial'
            elif 'vars' in k_lower or 'stimuli' in k_lower or 'noise' in k_lower \
                 or 'spike' in k_lower or 'raster' in k_lower or 'ts' in k_lower \
                 or 'event' in k_lower or 'emp' in k_lower:
                name = 'ts'
            elif k_lower.endswith('.h5'):
                convert.save_h5(sub[k], folders, ses=None)
                continue
            elif k_lower.endswith('txt') or k_lower.endswith('csv') or k_lower.endswith('dat'):
                name = 'coord'

            if name is not None:
                convert.save(sub[k], folders, ses=ses, name=name)

    # iterate over files and save them
    for k, v in subs.items():
        if 'ses-preop' in v.keys() or 'ses-postop' in v.keys():
            for k2, v2 in v.items():
                save(v2, ses=k2)
        else:
            save(v)


def check_output_folder():
    """ """
    # check if the output folder already contains files,
    # if true, notify about removal and remove folder with its contents
    conflict = len(os.listdir(OUTPUT)) > 0

    if conflict:
        pn.state.notifications.info('Output folder contains files. Removing them...')
        sim2bids.utils.rm_tree(OUTPUT)
        prep.reset_index()


def create_sub_struct(path, subs, ses_name=None):
    """

    Parameters
    ----------
    path :

    subs :

    ses_name :
         (Default value = None)

    Returns
    -------

    """
    if ses_name in ['ses-preop', 'ses-postop']:
        sub = os.path.join(path, subs['sid'])
        ses = os.path.join(sub, ses_name)
        net_ses = os.path.join(ses, 'net')
        spatial_ses = os.path.join(ses, 'spatial')
        coord_ses = os.path.join(ses, 'coord')
        ts_ses = os.path.join(ses, 'ts')
        folders = [sub, ses, net_ses, spatial_ses, coord_ses, ts_ses]
    else:
        sub = os.path.join(path, subs['sid'])
        net = os.path.join(sub, 'net')
        spatial = os.path.join(sub, 'spatial')
        ts = os.path.join(sub, 'ts')

        if MULTI_INPUT:
            coord = os.path.join(sub, 'coord')
            folders = [sub, net, spatial, coord, ts]
        else:
            folders = [sub, net, spatial, ts]

    for folder in folders:
        if not os.path.exists(folder):
            os.mkdir(folder)

    return folders


def save_code():
    """

    Parameters
    ----------
    subs :


    Returns
    -------

    """
    global MODEL_NAME

    template = f'desc-{DESC}_code.py'
    path = os.path.join(OUTPUT, 'code', template)

    if CODE is not None:
        shutil.copy(CODE, path)
        supply_dict('code', os.path.join(path.replace('py', 'json')))

        # save JSON files
        py2xml.main.XML(inp=CODE, output_path=os.path.join(OUTPUT, 'param'),
                        uid='delta_times', suffix=DESC, app=True)
        MODEL_NAME = utils.get_model()
        transfer_xml()


def transfer_xml():
    # transfer results to appropriate folders
    path = os.path.join(OUTPUT, 'param', f'desc-{DESC}_eq.xml')
    if os.path.exists(path):
        shutil.move(path, os.path.join(OUTPUT, 'eq'))

    # add json sidecars
    supply_dict('eq', os.path.join(OUTPUT, 'eq', f'desc-{DESC}_eq.json'))
    supply_dict('param', os.path.join(OUTPUT, 'param', f'desc-{DESC}_param.json'))

    # add json sidecar for model
    supply_dict('param', os.path.join(OUTPUT, 'param', f'model-{MODEL_NAME}_param.json'))


def supply_dict(ftype, path):
    file = OrderedDict()

    def get_dict(reqs):
        return {x: '' for x in temp.struct[ftype][reqs]}

    def save():
        with open(path, 'w') as f:
            json.dump(file, f)

    if len(temp.struct[ftype]['required']) > 0:
        file.update(get_dict('required'))

    file.update(get_dict('recommend'))

    eq = f'../eq/desc-{DESC}_eq.xml'

    # TODO: update when more models are added
    if ftype == 'code':
        file['ModelEq'] = eq
        file['Description'] = 'The source code to reproduce results.'
    elif ftype == 'param':
        file['ModelEq'] = eq
        file['Description'] = f'These are the parameters for the {MODEL_NAME} model for the delta series.'

    elif ftype == 'eq':
        if CODE is not None:
            code = os.path.basename(CODE)
            file['SourceCode'] = f'../code/{code}'

        file['Description'] = f'These are the equations to simulate the time series with the {MODEL_NAME} model.'

    save()


def remove_empty():
    """Recursively traverse generated output folder and remove all empty folders."""

    # get contents of the specified path
    for root, dirs, files in os.walk(OUTPUT):
        # if folder is empty, remove it
        if len(os.listdir(root)) == 0:
            os.removedirs(root)


def duplicate_folder(path):
    """

    Parameters
    ----------
    path :


    Returns
    -------

    """
    print('im triggered, duplicate folder')
    # create folder if it doesn't exist
    root = os.path.join('..', 'data')
    new_path = os.path.join(root, os.path.basename(os.path.dirname(path + '/')))

    if not os.path.exists(root):
        os.mkdir(root)

    if not os.path.exists(new_path):
        shutil.copytree(path, new_path, symlinks=False, ignore=None, ignore_dangling_symlinks=False,
                        dirs_exist_ok=False)
    # set PATH to a new path
    return new_path