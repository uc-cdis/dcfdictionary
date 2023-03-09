#!/usr/bin/env python3

import os
import sys
import re
import glob
import argparse
import pandas as pd
from datetime import datetime
from ruamel.yaml import YAML
from collections import defaultdict
from schema_utils import stripper
from ruamel.yaml.constructor import DuplicateKeyError

'''
#needs to be investigated
1. tosave = set() check usage
2. lrefs_to_srefs

'''


def csv_list(string):
    return string.split(',')


def get_params():
    """
    Parse the arguments passed to program
    """

    parser = argparse.ArgumentParser(description='name of directory containing yaml files, and TSV files.')
    parser.add_argument('-i', '--in_dir', dest='in_dir', required=True, help='Location of the yaml files')
    parser.add_argument('-o', '--out_dir', dest='out_dir', required=True, help='Destination of the tsv files')
    parser.add_argument('-d', '--dictionary', dest='dictionary', required=True, help='Name of the data dictionary')
    parser.add_argument('-e', '--extension', dest='extension', default='xlsx', choices= ['tsv', 'txt', 'xlsx'], help='Extension of the files saved')
    parser.add_argument('-y', '--yaml_files', dest='yaml_files', type=csv_list, default=[], help='Comma separated list of yaml files to be converted')
    parser.add_argument('-t', '--terms_file', dest='terms_file', action='store_true', help='Flag to generate terms file TSV')
    parser.add_argument('-f', '--first_import', dest='first_import', action='store_true', help='Flag to if its initial import')

    args = parser.parse_args()

    return args


def lrefs_to_srefs(refs):
    """
    Converts a list of references into a string
    """

    sref = ''

    for s in refs:
        if isinstance(s, dict):
            sref += s['$ref'] + ' ,'

    return sref


def get_linknames(dic):
    """
    Gets the names of links from links block so references can be made in
    properties list
    """

    out   = []
    links = dic['links']

    if links:
        for link in links:
            if type(link) == dict:
                try:
                    out.append(link['name'])

                except KeyError:
                    for l in link['subgroup']:
                        out.append(l['name'])

    return out


def get_yam_props(yamdics):
    """
    Scans & extracts the properties section in the yaml & excludes the link
    reference properties from the section
    """

    for d in yamdics:
        linknames = get_linknames(d)

        for l in linknames:
            if l in d['properties']:
                del d['properties'][l]

    yamprops = [(y['id'], y['properties']) for y in yamdics]

    return yamprops


def yam_filter(yam):
    """
    Filters out the yamls that will not be exported with the tool
    """

    # only following yamls are excluded
    # 'project', 'program', 'data_release', 'root' will be processed for GDC
    files = ['_settings', '_definitions', 'metaschema']

    for f in files:
        if f in yam:
            return False

    return True


def load_yams(in_dir, yaml_files, terms_file):
    """
    Load the yamls & apply filter
    """

    yamfiles     = glob.glob(in_dir+'*.yaml')
    filteredyams = list(filter(yam_filter, yamfiles))

    if terms_file:
        yaml_files = ['_terms']

    else:
        filteredyams = [f for f in filteredyams if '_terms.yaml' not in f]

    if yaml_files !=[]:
        temp_yams = []

        for f in yaml_files:
            for j in filteredyams:
                if f+'.yaml' == j.split('/')[-1]:
                    temp_yams.append(j)

        filteredyams= temp_yams.copy()

    filteredyams = sorted(filteredyams)

    yaml         = YAML(typ='safe')
    yamdics      = []

    for y in filteredyams:
        with open(y) as yam:
            try:
                yamdics.append(defaultdict(lambda: None, yaml.load(yam)))

            except DuplicateKeyError as e:
                print('ERROR: found duplicate key in {0}, check detailed error below: \n\n\n {1}'.format(y, e))

            except Exception as e:
                print('ERROR: error reading {0}. check detailed error below: \n\n\n {1}'.format(y, e))

    return yamdics, filteredyams


def get_terms_tobe(node, key, k, v, tmp_terms, ctr):

    if k == 'termDef':
        for block in v:
            prop_enum = 'property'

            if node==key:
                prop_enum = 'node'

            row = {'<property_or_enum>'    : key,
                   '<description>'         : '',
                   '<termDef:cde_id>'      : '',
                   '<termDef:cde_version>' : '',
                   '<termDef:source>'      : '',
                   '<termDef:term_id>'     : '',
                   '<termDef:term_version>': '',
                   '<termDef:term>'        : '',
                   '<termDef:term_url>'    : '',
                   '<node>'                : node,
                   '<enum_property>'       : '',
                   '<property/enum>'       : prop_enum
                  }

            for p,q in block.items():
                if p == 'term':
                    # if q != key:
                    #     sys.exit('ERROR: termDef mismatch found for {0} on node {1}'.format(key, node))
                    # else:
                    row['<termDef:term>'] = q

                elif p == 'source':
                    row['<termDef:source>'] = q

                elif p == 'term_id':
                    row['<termDef:cde_id>'] = q

                elif p == 'term_version':
                    row['<termDef:cde_version>'] = q

                else:
                    row['<'+p+'>'] = q

            tmp_terms[ctr] = row
            ctr += 1

    elif k == 'enumDef':
        for block in v:
            row = {'<property_or_enum>'    : '', #
                   '<description>'         : '',
                   '<termDef:cde_id>'      : '',
                   '<termDef:cde_version>' : '',
                   '<termDef:source>'      : '', #
                   '<termDef:term_id>'     : '', #
                   '<termDef:term_version>': '', #
                   '<termDef:term>'        : '',
                   '<termDef:term_url>'    : '',
                   '<node>'                : node,
                   '<enum_property>'       : key,
                   '<property/enum>'       : 'enum'
                  }

            for p,q in block.items():
                if p == 'enumeration':
                    row['<property_or_enum>'] = q

                elif p == 'source':
                    row['<termDef:source>'] = q

                elif p == 'term_id':
                    row['<termDef:term_id>'] = q

                elif p in ['term_version', 'version_date']:
                    row['<termDef:term_version>'] = q

                else:
                    row['<'+p+'>'] = q

            tmp_terms[ctr] = row
            ctr += 1

    return tmp_terms, ctr


def get_var_values(props, val_dict, enum_dict, tmp_terms, ctr):
    """
    Gets the fields and values from the properties portion of the yaml file and
    adds it to the dataframe.

    Arguments:
        props {[dictionary]} -- [yaml properties]
        val_dict {[dictionary]} -- [The dict of dict which will be converted to
                                    dataframe and exported as a csv]

    Returns:
        [dictionary] -- [Returns a dict of dict with the fields and their
                         values from the properties part of the yaml file]
    """

    for key, val in props[1].items():
        if isinstance(key, str) and key == '$ref':
            continue

        row = {'<node>'       : props[0],
               '<property>'   : key,
               '<terms>'      : None,
               '<description>': None,
               '<type>'       : None,
               '<pattern>'    : None,
               '<maximum>'    : None,
               '<minimum>'    : None
              }

        if isinstance(val, dict):
            enums      = val.get('enum')
            enum_def   = val.get('enumDef')
            dep_enum   = val.get('deprecated_enum')
            temp_enums = {}

            for k, v in val.items():
                if k in ['deprecated_enum', 'enumDef', 'enumTerms']:
                    continue

                elif k in ['enum']: #, 'deprecated_enum', 'enumDef', 'enumTerms']: TESTING DO NOT DELETE
                    row['<type>'] = 'enum'

                elif k == 'type':
                    if v == 'array':
                        row['<type>'] = 'array'
                        print('its an Array!!!! {0} on {1}'.format(key, props[0]))

                    elif isinstance(v, list):
                        row['<type>'] = ', '.join(v)

                    elif isinstance(v, str):
                        row['<type>'] = stripper(v)

                elif k == 'oneOf':
                    temp_type = []

                    for t_dict in v:
                        for m, n in t_dict.items():
                            if m == 'type':
                                temp_type.append(stripper(n))

                            elif m in ['pattern', 'maximum', 'minimum']:
                                row['<'+m+'>'] = stripper(n)

                    row['<type>'] = ', '.join(temp_type)

                elif k in ['$ref', 'term', 'terms']:
                    val_l = None

                    if isinstance(v, dict):
                        val_l = v.get('$ref')

                        if isinstance(val_l, str):
                            val_l = [stripper(val_l)]

                    elif isinstance(v, str):
                        val_l = [stripper(v)]

                    elif isinstance(v, list):
                        val_l = v

                    if val_l:
                        val_l_common = []

                        for val_ in val_l:
                            if '_terms.yaml#/' in val_ and '/common' not in val_:
                                val_ += '/common'

                            val_l_common.append(val_)

                        row['<terms>'] = ', '.join(val_l_common)

                elif k == 'termDef':
                    tmp_terms, ctr = get_terms_tobe(props[0], key, k, v, tmp_terms, ctr)

                elif k == 'items':
                    for p, q in v.items():
                        if p in [ '$ref', 'type']:
                            row['<items>'] = q

                        elif p == 'enum':
                            row['<items>'] = 'enum'

                            for e in q:
                                enum_row = {'<node>'       : props[0],
                                            '<property>'   : key,
                                            '<enum_value>' : e, # validate_text(e),
                                            '<enum_def>'   : None,
                                            '<deprecated>' : None
                                           }

                                temp_enums[props[0]+':'+key+':'+e] = enum_row

                        else:
                            row['<'+p+'>'] = q

                else:
                    row['<'+k+'>'] = v

            if enums:
                for e in enums:
                    enum_row = {'<node>'       : props[0],
                                '<property>'   : key,
                                '<enum_value>' : e, # validate_text(e),
                                '<enum_def>'   : None,
                                '<deprecated>' : None
                               }

                    temp_enums[props[0]+':'+key+':'+e] = enum_row

            if enum_def:
                if isinstance(enum_def, list):
                    tmp_terms, ctr = get_terms_tobe(props[0], key, 'enumDef', enum_def, tmp_terms, ctr)

                elif isinstance(enum_def, dict):
                    for k, v in enum_def.items():
                        temp_enums[props[0]+':'+key+':'+k]['<enum_def>'] = ', '.join(v['$ref'])

                else:
                    print('Something is really weird about enum_Def')

            if dep_enum:
                for e in dep_enum:
                    enum_row = {'<node>'       : props[0],
                                '<property>'   : key,
                                '<enum_value>' : e, # validate_text(e),
                                '<enum_def>'   : None,
                                '<deprecated>' : 'yes'
                               }

                    temp_enums[props[0]+':'+key+':'+'dep_'+e] = enum_row

        else:
            sys.exit('The property {0} on node {1} is not defined properly. \n Only $ref can be defined as list in the yaml, all other properties should have atleast one key : value pair under it'.format(key, props[0]))

        for k, v in temp_enums.items():
            enum_dict[k] = v

        val_dict[props[0]+':'+key] = row

    return val_dict, enum_dict, tmp_terms, ctr


def get_links(links, row):
    """
    Process & flatten the links section in the yaml. Values within the subgroup
    are comma separated & the subgroups are pipe separated.
    """

    l_name_str         = []
    l_backref_str      = []
    l_label_str        = []
    l_target_str       = []
    l_multiplicity_str = []
    l_required_str     = []
    g_exclusive_str    = []
    g_required_str     = []

    for link in links:
        if isinstance(link, dict) and link != {}:
            if 'subgroup' in link:
                sub_name    = []
                sub_backref = []
                sub_label   = []
                sub_target  = []
                sub_multi   = []
                sub_req     = []

                for l in link['subgroup']:
                    sub_name.append(l['name'])
                    sub_backref.append(l['backref'])
                    sub_label.append(l['label'])
                    sub_target.append(l['target_type'])
                    sub_multi.append(l['multiplicity'])
                    sub_req.append(str(l['required']).title())

                l_name_str.append(', '.join(sub_name))
                l_backref_str.append(', '.join(sub_backref))
                l_label_str.append(', '.join(sub_label))
                l_target_str.append(', '.join(sub_target))
                l_multiplicity_str.append(', '.join(sub_multi))
                l_required_str.append(', '.join(sub_req))
                g_exclusive_str.append(str(link['exclusive']).title())
                g_required_str.append(str(link['required']).title())

            else:
                try:
                    l_name_str.append(link['name'])
                    l_backref_str.append(link['backref'])
                    l_label_str.append(link['label'])
                    l_target_str.append(link['target_type'])
                    l_multiplicity_str.append(link['multiplicity'])
                    l_required_str.append(str(link['required']).title())
                    g_exclusive_str.append('')
                    g_required_str.append('')

                except KeyError:
                    pass

    row['<link_name>']            = ' | '.join(l_name_str)
    row['<link_backref>']         = ' | '.join(l_backref_str)
    row['<link_label>']           = ' | '.join(l_label_str)
    row['<link_target>']          = ' | '.join(l_target_str)
    row['<link_multiplicity>']    = ' | '.join(l_multiplicity_str)
    row['<link_required>']        = ' | '.join(l_required_str)
    row['<link_group_exclusive>'] = ' | '.join(g_exclusive_str)
    row['<link_group_required>']  = ' | '.join(g_required_str)

    return row


def get_node_values(temp_node, node_dict, tmp_terms, ctr):
    """
    Gets the values of the fields in the nodes schema, inputs their values into
    the row dictionary. Then appends dictionary to the nodes dataframe.

    Arguments:
        temp_node {[dictionary]} -- [The yaml file in dictionary form]
        node_dict {[dictionary]} -- [The dict of dict which will be converted
                                     to dataframe and exported as a csv]

    Returns:
        [dictionary] -- [Returns a dict of dict with the fields and their
                         values from the node part of the yaml file]
    """

    node = dict(temp_node)
    row  = {}

    for k, v in node.items():
        if k not in ['links', 'properties', 'preferred', 'constraints']:
            if k == 'required':
                row['<'+k+'>'] = ', '.join(v)

            elif k == 'systemProperties':
                row['<'+k+'>'] = ', '.join(v)

            elif k == 'deprecated':
                if v:
                    v = ', '.join(v)

                row['<'+k+'>'] = v

            elif k == 'uniqueKeys':
                row['<'+k+'>'] = ' | '.join([', '.join(i) for i in v])

            elif k == 'termDef':
                tmp_terms, ctr = get_terms_tobe(node['id'], node['id'], k, v, tmp_terms, ctr)

            else:

                if v in [False, True]:
                    v = str(v).title()

                row['<'+k+'>'] = v

    row     = get_links(node['links'], row)
    propref = node['properties'].get('$ref')

    if propref is not None:

        if isinstance(propref, list):
            propref = [stripper(x) for x in propref]

        elif isinstance(propref, str):
            propref = [stripper(propref)]

        row['<property_ref>'] = ', '.join(propref)

    try:
        nterms = node['<nodeTerms>']

    except:
        nterms = None

    if nterms is not None:
        row['<nodeTerms>'] = lrefs_to_srefs(nterms)

    node_dict[node['id']] = row

    return node_dict, tmp_terms, ctr


def export_nodes_props(yamdics, out_dir, dictionary, extension):
    """
    Export node schema to TSV
    """

    yamprops  = get_yam_props(yamdics)

    # create the nodes tsv
    node_dict = {}
    tmp_terms = {}
    ctr = 1

    for dic in yamdics:
        node_dict, tmp_terms, ctr = get_node_values(dic, node_dict, tmp_terms, ctr)

    # create the properties & enum tsvs
    val_dict  = {}
    enum_dict = {}

    for props in yamprops:
        val_dict, enum_dict, tmp_terms, ctr = get_var_values(props, val_dict, enum_dict, tmp_terms, ctr)

    ndf = pd.DataFrame.from_dict(node_dict, orient='index')
    vdf = pd.DataFrame.from_dict(val_dict, orient='index')
    edf = pd.DataFrame.from_dict(enum_dict, orient='index')

    if tmp_terms:
        ttdf = pd.DataFrame.from_dict(tmp_terms, orient='index')

    if extension == 'xlsx':
        writer = pd.ExcelWriter('{0}nodes_schema_{1}.xlsx'.format(out_dir, dictionary), engine = 'xlsxwriter')

        ndf.to_excel(writer, index = False, sheet_name = 'nodes_{0}'.format(dictionary))
        vdf.to_excel(writer, index = False, sheet_name = 'variables_{0}'.format(dictionary))
        edf.to_excel(writer, index = False, sheet_name = 'enums_{0}'.format(dictionary))

        writer.save()

        if tmp_terms:
            t_writer = pd.ExcelWriter('{0}terms_to_be_migrated_{1}.xlsx'.format(out_dir, dictionary), engine = 'xlsxwriter')

            ttdf.to_excel(t_writer, index = False, sheet_name = 'terms_to_be_migrated')

            t_writer.save()

    else:
        ndf.to_csv('{0}nodes_{1}.{2}'.format(out_dir, dictionary, extension), sep = '\t', index = False, quoting = None)
        vdf.to_csv('{0}variables_{1}.{2}'.format(out_dir, dictionary, extension), sep = '\t', index = False, quoting = None)
        edf.to_csv('{0}enums_{1}.{2}'.format(out_dir, dictionary, extension), sep = '\t', index = False, quoting = None)

        if tmp_terms:
            ttdf.to_csv('{0}terms_to_be_migrated_{1}.{2}'.format(out_dir, dictionary, extension), sep = '\t', index = False, quoting = None)


    '''
    #needs to be investigated
    for fi in tosave:
        if fi in filteredyams:
            with open(fi) as saveyam:
                syam = saveyam.read()

            with open('{0}_archive.yaml'.format(fi[:-5]), 'w') as saver:
                saver.write(syam)
    '''

    print('*'*100, '\n')
    print(' '*42, 'YAML  ---->  TSV', ' '*42, '\n')
    print('*'*100, '\n')
    print('Source Directory      : {0}'.format(in_dir))

    if extension == 'xlsx':
        print('Generated Files       : nodes_schema_{0}.xlsx'.format(dictionary), '\n')

    else:
        print('Generated Files       : nodes_{0}.{1}'.format(dictionary, extension))
        print(' '*24+'variables_{0}.{1}'.format(dictionary, extension))
        print(' '*24+'enums_{0}.{1}'.format(dictionary, extension), '\n')

    print('Number of Nodes       : {0}'.format(ndf.shape[0]))
    print('Number of Properties  : {0}'.format(vdf.shape[0]), '\n')
    print('Destination Directory : {0}'.format(out_dir))
    print('*'*100, '\n')


def enrich_terms(yamprops, terms_dict, enum_terms_dict):
    """
    Scan all the node yamls and add all the properties & enum values to terms
    tsv if its not already present
    """

    for props in yamprops:
        for key, val in props[1].items():
            if isinstance(key, str) and key == '$ref':
                continue

            if key+':common' not in terms_dict :
                if isinstance(val, dict):
                    try:
                        refs = val.get('term').get('$ref')

                    except:
                        refs = None

                    if refs != [] and refs is not None:
                        for ref in refs:
                            if ref == '_terms.yaml#/'+key+'/common':
                                row = {'<property_or_enum>'    : key, # validate_text(key),
                                       '<description>'         : '',
                                       '<termDef:cde_id>'      : '',
                                       '<termDef:cde_version>' : '',
                                       '<termDef:source>'      : '',
                                       '<termDef:term_id>'     : '',
                                       '<termDef:term_version>': '',
                                       '<termDef:term>'        : '',
                                       '<termDef:term_url>'    : '',
                                       '<node>'                : 'common',
                                       '<enum_property>'       : ''
                                       }

                                terms_dict[key+':common'] = row

                            elif '_terms.yaml#/' in ref:
                                sys.exit('ERROR : Term def urls for "{0}" on "{1}" node are not in standard format, please fix them'.format(key, props[0]))

                    else:
                        row = {'<property_or_enum>'    : key, # validate_text(key),
                               '<description>'         : '',
                               '<termDef:cde_id>'      : '',
                               '<termDef:cde_version>' : '',
                               '<termDef:source>'      : '',
                               '<termDef:term_id>'     : '',
                               '<termDef:term_version>': '',
                               '<termDef:term>'        : '',
                               '<termDef:term_url>'    : '',
                               '<node>'                : props[0],
                               '<enum_property>'       : '',
                               '<property/enum>'       : 'property'
                               }

                        enum_terms_dict[key+':common'] = row

            if isinstance(val, dict):
                enums     = []
                enum_defs = {}

                for k, v in val.items():
                    if k == 'enum':
                        enums = v

                    if k == 'enumDef':
                        enum_defs = v

                if enums != []:
                    for enum in enums:
                        if enum in enum_defs:
                            for ref in enum_defs[enum]['$ref']:
                                ref_key  = None
                                ref_prop = None
                                ref_node = None
                                ref_enum = None

                                if ref == '_terms.yaml#/'+re.sub('[\W]+', '', enum.lower().strip().replace(' ', '_'))+'/'+props[0]+'/'+key:
                                    ref_key  = re.sub('[\W]+', '', enum.lower().strip().replace(' ', '_'))+':'+props[0]+':'+key
                                    ref_prop = re.sub('[\W]+', '', enum.lower().strip().replace(' ', '_'))
                                    ref_node = props[0]
                                    ref_enum = key

                                elif ref == '_terms.yaml#/'+re.sub('[\W]+', '', enum.lower().strip().replace(' ', '_'))+'/common':
                                    ref_key  = re.sub('[\W]+', '', enum.lower().strip().replace(' ', '_'))+':common'
                                    ref_prop = re.sub('[\W]+', '', enum.lower().strip().replace(' ', '_'))
                                    ref_node = 'common'
                                    ref_enum = ''

                                elif '_terms.yaml#/' in ref:
                                    sys.exit('ERROR : Enum def urls for "{0} - {1}" on "{2}" node are not in standard format, please fix them'.format(key, enum, props[0]))

                                if ref_key and ref_key not in terms_dict:
                                    row = {'<property_or_enum>'    : ref_prop, # validate_text(ref_prop),
                                           '<description>'         : '',
                                           '<termDef:cde_id>'      : '',
                                           '<termDef:cde_version>' : '',
                                           '<termDef:source>'      : '',
                                           '<termDef:term_id>'     : '',
                                           '<termDef:term_version>': '',
                                           '<termDef:term>'        : '',
                                           '<termDef:term_url>'    : '',
                                           '<node>'                : ref_node,
                                           '<enum_property>'       : ref_enum
                                           }

                                    terms_dict[ref_key] = row

                        else:
                            row = {'<property_or_enum>'    : enum, # validate_text(enum),
                                   '<description>'         : '',
                                   '<termDef:cde_id>'      : '',
                                   '<termDef:cde_version>' : '',
                                   '<termDef:source>'      : '',
                                   '<termDef:term_id>'     : '',
                                   '<termDef:term_version>': '',
                                   '<termDef:term>'        : '',
                                   '<termDef:term_url>'    : '',
                                   '<node>'                : props[0],
                                   '<enum_property>'       : key,
                                   '<property/enum>'       : 'enum'
                                   }

                            enum_terms_dict[enum+':'+props[0]+':'+key] = row

    return terms_dict, enum_terms_dict


def export_terms(terms, in_dir, out_dir, dictionary, extension):
    """
    Process _terms.yaml file and generate TSV file
    """

    terms_dict      = {}
    enum_terms_dict = {}

    for key, val in terms.items():
        if isinstance(key, str) and key == 'id':
            continue

        row = {'<property_or_enum>': key}

        for k, v in val.items():
            if k == 'termDef':
                for i,j in v.items():
                    row['<'+k+':'+i+'>'] = j

            elif k == 'description':
                row['<'+k+'>'] = ' '.join(v.strip().split(' '))

            else:
                row['<'+k+'>'] = v

        row['<termDef:term_id>']      = ''
        row['<termDef:term_version>'] = ''
        row['<node>']                 = 'common'
        row['<enum_property>']        = ''

        terms_dict[key+':common']     = row


    yamdics_no_terms, filteredyams_no_terms = load_yams(in_dir, [], False)

    yamprops_no_terms = get_yam_props(yamdics_no_terms)

    terms_dict, enum_terms_dict = enrich_terms(yamprops_no_terms, terms_dict, enum_terms_dict)

    tdf = pd.DataFrame.from_dict(terms_dict, orient='index')

    etdf = pd.DataFrame.from_dict(enum_terms_dict, orient='index')
    etdf = etdf.sort_values(by=['<property/enum>','<node>','<enum_property>','<property_or_enum>'])

    if extension == 'xlsx':
        writer = pd.ExcelWriter('{0}terms_schema_{1}.xlsx'.format(out_dir, dictionary), engine = 'xlsxwriter')

        tdf.to_excel(writer, index = False, sheet_name = 'terms_{0}'.format(dictionary))
        etdf.to_excel(writer, index = False, sheet_name = 'missing_term_reference_{0}'.format(dictionary)[0:30])

        writer.save()

    else:
        tdf.to_csv('{0}terms_{1}.{2}'.format(out_dir, dictionary, extension), sep = '\t', index = False, quoting = None)
        etdf.to_csv('{0}missing_term_reference_{1}.{2}'.format(out_dir, dictionary, extension), sep = '\t', index = False, quoting = None)

    print('*'*100, '\n')
    print(' '*42, 'YAML  ---->  TSV', ' '*42, '\n')
    print('*'*100, '\n')
    print('Source Directory      : {0}'.format(in_dir))

    if extension == 'xlsx':
        print('Generated Files       : terms_schema_{0}.xlsx'.format(dictionary), '\n')

    else:
        print('Generated Files       : terms_{0}.{1}'.format(dictionary, extension))
        print(' '*24+'missing_term_reference_{0}.{1}'.format(dictionary, extension), '\n')

    print('Number of Terms       : {0}'.format(tdf.shape[0]))
    print('Number of Enums       : {0}'.format(etdf.shape[0]), '\n')
    print('Destination Directory : {0}'.format(out_dir))
    print('*'*100, '\n')


def export_terms_future(terms, in_dir, out_dir, dictionary, extension):
    """
    Process _terms.yaml file and generate TSV file
    Copy of export_terms with support for extracting node & enum property info
    from the term
    """

    terms_dict      = {}
    enum_terms_dict = {}

    for key, val in terms.items():
        if isinstance(key, str) and key == 'id':
            continue

        for k, v in val.items():
            if k == 'common':
                row = {'<property_or_enum>': key}

                for i,j in v.items():
                    if i == 'termDef':
                        for m,n in j.items():
                            if n:
                                row['<'+i+':'+m+'>'] = str(n)

                            else:
                                row['<'+i+':'+m+'>'] = n

                    elif i == 'description':
                        if j:
                            row['<'+i+'>'] = ' '.join(j.strip().split(' '))

                        else:
                            row['<'+i+'>'] = None

                    else:
                        row['<'+i+'>'] = j

                row['<node>']          = k
                row['<enum_property>'] = ''

                terms_dict[key+':'+k]  = row

            else:
                for i,j in v.items():
                    row = {'<property_or_enum>': key}

                    for c,d in j.items():
                        if c == 'termDef':
                            for m,n in d.items():
                                if n:
                                    row['<'+c+':'+m+'>'] = str(n)

                                else:
                                    row['<'+c+':'+m+'>'] = n
                        
                        elif c == 'description':
                            if d:
                                row['<'+c+'>'] = ' '.join(d.strip().split(' '))

                            else:
                                row['<'+c+'>'] =  None

                        else:
                            row['<'+c+'>'] = d

                    row['<node>']               = k
                    row['<enum_property>']      = i

                    terms_dict[key+':'+k+':'+i] = row


    yamdics_no_terms, filteredyams_no_terms = load_yams(in_dir, [], False)

    yamprops_no_terms = get_yam_props(yamdics_no_terms)

    terms_dict, enum_terms_dict = enrich_terms(yamprops_no_terms, terms_dict, enum_terms_dict)

    tdf = pd.DataFrame.from_dict(terms_dict, orient='index')

    etdf = pd.DataFrame.from_dict(enum_terms_dict, orient='index')
    etdf = etdf.sort_values(by=['<property/enum>','<node>','<enum_property>','<property_or_enum>'])

    if extension == 'xlsx':
        writer = pd.ExcelWriter('{0}terms_schema_{1}.xlsx'.format(out_dir, dictionary), engine = 'xlsxwriter')

        tdf.to_excel(writer, index = False, sheet_name = 'terms_{0}'.format(dictionary))
        etdf.to_excel(writer, index = False, sheet_name = 'missing_term_reference_{0}'.format(dictionary)[0:30])

        writer.save()

    else:
        tdf.to_csv('{0}terms_{1}.{2}'.format(out_dir, dictionary, extension), sep = '\t', index = False, quoting = None)
        etdf.to_csv('{0}missing_term_reference_{1}.{2}'.format(out_dir, dictionary, extension), sep = '\t', index = False, quoting = None)
        #csv.QUOTE_ALL, quotechar='"')

    print('*'*100, '\n')
    print(' '*42, 'YAML  ---->  TSV', ' '*42, '\n')
    print('*'*100, '\n')
    print('Source Directory      : {0}'.format(in_dir))

    if extension == 'xlsx':
        print('Generated Files       : terms_schema_{0}.xlsx'.format(dictionary), '\n')

    else:
        print('Generated Files       : terms_{0}.{1}'.format(dictionary, extension))
        print(' '*24+'missing_term_reference_{0}.{1}'.format(dictionary, extension), '\n')

    print('Number of Terms       : {0}'.format(tdf.shape[0]))
    print('Number of Enums       : {0}'.format(etdf.shape[0]), '\n')
    print('Destination Directory : {0}'.format(out_dir))
    print('*'*100, '\n')


if __name__ == '__main__':

    temp_st_time = datetime.now()
    args         = get_params()

    in_dir       = args.in_dir
    out_dir      = args.out_dir
    dictionary   = args.dictionary
    extension    = args.extension
    yaml_files   = args.yaml_files
    terms_file   = args.terms_file
    first_import = args.first_import


    if in_dir[-1] != '/':
        in_dir += '/'

    if out_dir[-1] != '/':
        out_dir += '/'

    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    yamdics, filteredyams = load_yams(in_dir, yaml_files, terms_file)

    if terms_file:
        # export_terms is for first time migration & export_terms_future is for future use
        if first_import:
            export_terms(yamdics[0], in_dir, out_dir, dictionary, extension)

        else:
            export_terms_future(yamdics[0], in_dir, out_dir, dictionary, extension)

    else:
        export_nodes_props(yamdics, out_dir, dictionary, extension)

    temp_fin_time = datetime.now()

    print('\n\tTotal time for YAML <> TSV generation   : ' + str(temp_fin_time - temp_st_time))
