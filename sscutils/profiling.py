from dataclasses import dataclass, asdict, field
from typing import List
from subprocess import check_call
import json
from urllib.parse import urlencode
import requests
import yaml
import os
from sscutils.naming import DATASET_METADATA_PATHS

@dataclass
class ERPlot:
    tables: dict = field(default_factory = dict)
    relations: List[str] = field(default_factory=list)
    rankAdjustments: str = ''
    label: str = ''

    def _parse(self):
        
        for table_name, table_data in self.table_schemas.items():

            if 'features' in table_data.keys():
                for feature in table_data['features']:
                    if 'name' in feature.keys():
                        self.tables[table_name][feature['name']] = feature['dtype']
                    if 'prefix' in feature.keys():
                        if 'table' in feature.keys():
                            for foreign_key, foreign_type in [key for key in self.tables[feature['table']].items() if key[0].startswith('*')]:
                                self.tables[table_name]['+' + feature['prefix']] = foreign_type
                                self._add_relation(table_name, feature['prefix'], feature['table'], foreign_key[1:])
                        elif 'dtype' in feature.keys():
                            for foreign in self.composite_types[feature['dtype']]['features']:
                                if 'name' in foreign.keys():
                                    self.tables[table_name][feature['prefix'] + '__' + foreign['name']] = foreign['dtype']
                                elif 'prefix' in foreign.keys():
                                    for foreign_key, foreign_type in [key for key in self.tables[foreign['table']].items() if key[0].startswith('*')]:
                                        self.tables[table_name]['+' + feature['prefix'] + '__' + foreign['prefix']] = foreign_type
                                        self._add_relation(table_name, feature['prefix'] + '__' + foreign['prefix'], foreign['table'], foreign_key.split('__')[0][1:], )
                        
    def _add_relation(self, left_table, left_feature, right_table, right_featue) -> None:
        self.relations.append(
            f'{left_table}:{left_feature} -- {right_table}:{right_featue}'
        )

    def _parse_tables(self):
        for table_name, _ in self.table_schemas.items():
            self.tables[table_name] = dict()

    def _parse_indexes(self):
        for table_name, table_data in self.table_schemas.items():
            if 'index' in table_data.keys():
                for index in table_data['index']:
                    if 'name' in index.keys():
                        self.tables[table_name]['*' + index['name']] = index['dtype']
                    elif 'prefix' in index.keys():
                        if 'table' in index.keys():
                            for foreign in self.table_schemas[index['table']]['index']:
                                self.tables[table_name]['*' + index['prefix']] = foreign['dtype']
                                self._add_relation(table_name, index['prefix'], index['table'], foreign['name'])
                        elif 'dtype' in index.keys():
                            for foreign in self.composite_types[index['dtype']]['features']:
                                if 'name' in foreign.keys():
                                    self.tables[table_name]['*' + index['prefix'] + '__' + foreign['name']] = foreign['dtype']

    def _import_data(self):
        self.table_schemas = yaml.load(DATASET_METADATA_PATHS.table_schemas.open(), Loader=yaml.FullLoader)
        self.composite_types = yaml.load(DATASET_METADATA_PATHS.composite_types.open(), Loader=yaml.FullLoader)

    def get_diagram(self):
        self._import_data()
        self._parse_tables()
        self._parse_indexes()
        self._parse()
        self._save_ERDYAML()
        self._generate_dot_file()
        self._generate_figure()
        self._remove_files()

    def _save_ERDYAML(self):
        with open('ERDYAML.yaml', 'w') as file:
            yaml.dump(asdict(self), file)

    def _generate_dot_file(self):
        check_call(['erdot', 'ERDYAML.yaml'], cwd=os.getcwd())

    def _generate_figure(self):
        with open('ERDYAML.dot') as file:
            graph_data = file.read()

        postdata = {
        "graph": graph_data,
        "layout": "dot",
        "format": "png"
        }

        url = f'https://quickchart.io/graphviz?{urlencode(postdata)}'
        r = requests.get(url, allow_redirects=True)

        with open('ER_diagram.png', 'wb') as file:
            file.write(r.content)

    def _remove_files(self):
        os.remove('ERDYAML.yaml')
        os.remove('ERDYAML.dot')