import io
import os
import pandas as pd
from pathlib import Path
import incf.preprocess.preprocess as prep

import json
import sys
import csv

sys.path.append('..')


def check_file(og_path, values, output='../output', save=False):
    # create dictionary to store values
    subs = {}

    for val in values:
        # get the absolute path
        path = os.path.join(og_path, val)

        # get filename without file extension
        name = os.path.basename(val).split('.')[0]

        # create subjects
        subs[val] = {'name': val, 'sid': prep.create_uuid(), 'sep': find_separator(path),
                     'desc': 'default', 'path': path, 'fname': name}

        # add new id to make sure there's no overlap in folder creation
        prep.IDS.append(subs[val]['sid'])

    # create folders if required
    if save:
        create_output_folder(output, subs)

    # generate folder structure layout
    layout = create_layout(subs, output)

    return layout


def find_separator(path):
    """
    Find the separator/delimiter used in the file to ensure no exception
    is raised while reading files.

    :param path:
    :return:
    """

    sniffer = csv.Sniffer()
    with open(path) as fp:
        delimiter = sniffer.sniff(fp.read(500)).delimiter
    return delimiter


def save_files(subs, output):
    pass


def create_layout(subs=None, output='../output'):
    """
    Create folder structure according to BEP034 and passed `subs` parameter.

    :param output:
    :param subs:
    :return:
    """

    output = output.replace('.', '').replace('/', '')
    layout = create_sub(subs)
    layout = '&emsp;'.join(layout) if len(layout) > 1 else ''.join(layout)

    return f"""
    {output}/ <br>
        &emsp;|___ code <br>
        &emsp;|___ eq <br>
        &emsp;|___ param <br>
        &emsp;{layout}
        &emsp;|___ README <br>
        &emsp;|___ CHANGES <br>
        &emsp;|___ dataset_description.json <br>
        &emsp;|___ participants.tsv
    """


def create_sub(subs):
    outputs = []
    centers_found = False

    for k, v in subs.items():
        print(k, v, end='\n\n')

        name = subs[k]['name'].split('.')[0]
        if subs[k]['name'] == 'weights.txt':
            outputs.append(f"""|___ sub-{subs[k]['sid']} <br>
                        &emsp;&emsp;&emsp;|___ net <br>
                            &emsp;&emsp;&emsp;&emsp;|___ sub-{subs[k]['sid']}_desc-{subs[k]['desc']}_{name}.tsv <br>
                            &emsp;&emsp;&emsp;&emsp;|___ sub-{subs[k]['sid']}_desc-{subs[k]['desc']}_{name}.json <br>
                        &emsp;&emsp;&emsp;|___ spatial <br>
                        &emsp;&emsp;&emsp;|___ ts  <br>
                    """)
        elif subs[k]['name'] == 'distances.txt':
            outputs.append(f"""|___ sub-{subs[k]['sid']} <br>
                         &emsp;&emsp;&emsp;|___ net <br>
                             &emsp;&emsp;&emsp;&emsp;|___ sub-{subs[k]['sid']}_desc-{subs[k]['desc']}_{name}.tsv <br>
                             &emsp;&emsp;&emsp;&emsp;|___ sub-{subs[k]['sid']}_desc-{subs[k]['desc']}_{name}.json <br>
                         &emsp;&emsp;&emsp;|___ spatial <br>
                         &emsp;&emsp;&emsp;|___ ts  <br>
                    """)
        elif subs[k]['name'] in ['centres.txt', 'centers.txt']:
            outputs.append(f"""|___ coord <br>
                        &emsp;&emsp;&emsp;|___ desc-{subs[k]['desc']}_nodes.json <br>
                        &emsp;&emsp;&emsp;|___ desc-{subs[k]['desc']}_labels.json <br>
                        &emsp;&emsp;&emsp;|___ desc-{subs[k]['desc']}_nodes.tsv <br>
                        &emsp;&emsp;&emsp;|___ desc-{subs[k]['desc']}_labels.tsv <br>
            """)
            centers_found = True

    if not centers_found:
        outputs.append('|___ coord <br>')
    return outputs


def create_output_folder(path, subs: dict):
    # verify folders exist
    check_folders(path)

    for k, v in subs.items():
        if k in ['weights.txt', 'distances.txt']:
            create_weights_distances(path, subs[k])
        if k in ['centres.txt', 'centers.txt', 'centre.txt', 'center.txt']:
            create_centers(path, subs[k])


def create_weights_distances(path, subs):
    sub = os.path.join(path, f"sub-{subs['sid']}")
    net = os.path.join(sub, 'net')

    if not os.path.exists(sub):
        print(f'Creating folder `{sub}`')
        os.mkdir(sub)

    if not os.path.exists(net):
        print(f'Creating folder `{net}`')
        os.mkdir(net)

    fname = f'sub-{subs["sid"]}_desc-default_{subs["fname"]}'

    f = pd.read_csv(subs['path'], sep=subs['sep'], index_col=None, header=None)
    f.to_csv(os.path.join(net, fname + '.tsv'), sep='\t', header=None, index=None)

    shape = f.shape

    json_file = {
        'NumberOfRows': shape[0],
        'NumberOfColumns': shape[1],
        'CoordsRows': '',
        'CoordsColumns': '',
        'Description': ''
    }

    with open(os.path.join(net, fname + '.json'), 'w') as outfile:
        json.dump(json_file, outfile)


def create_centers(path, subs):
    f = pd.read_csv(subs['path'], sep=subs['sep'], index_col=None, header=None)
    print(f)
    print(subs)
    labels, nodes = f[0], f[[1, 2, 3]]

    # save in `.tsv` format
    labels.to_csv(os.path.join(path, 'coord', f'desc-{subs["desc"]}_labels.tsv'), header=None, index=None)
    nodes.to_csv(os.path.join(path, 'coord', f'desc-{subs["desc"]}_nodes.tsv'), sep='\t', header=None, index=None)

    # save in `.json` format
    with open(os.path.join(path, 'coord', f'desc-{subs["desc"]}_labels.json'), 'w') as outfile:
        json.dump({'NumberOfRows': labels.shape[0], 'NumberOfColumns': 1, 'Units': '', 'Description': ''}, outfile)

    with open(os.path.join(path, 'coord', f'desc-{subs["desc"]}_nodes.json'), 'w') as outfile:
        json.dump({'NumberOfRows': nodes.shape[0], 'NumberOfColumns': nodes.shape[1],
                   'Units': '', 'Description': ''}, outfile)


def check_folders(path):
    eq = os.path.join(path, 'eq')
    code = os.path.join(path, 'code')
    coord = os.path.join(path, 'coord')
    param = os.path.join(path, 'param')

    for p in [path, eq, code, coord, param]:
        if not os.path.exists(p):
            print(f'Creating folder `{os.path.basename(p)}`...')
            os.mkdir(p)

    read = os.path.join(path, 'README.txt')
    part = os.path.join(path, 'participants.tsv')
    desc = os.path.join(path, 'dataset_description.json')
    chgs = os.path.join(path, 'CHANGES.txt')

    for p in [read, part, desc, chgs]:
        if not os.path.exists(p):
            print(f'Creating file `{os.path.basename(p)}`...')
            Path(p).touch()
