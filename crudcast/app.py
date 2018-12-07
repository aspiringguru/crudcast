import pymongo
from yaml import load
from flask import Flask
from flask_swagger_ui import get_swaggerui_blueprint
from .models import Model


class CrudcastApp(Flask):
    crudcast_config = {
        # database
        "mongo_url": "mongodb://localhost:27017/",
        "db_name": "database",

        # swagger
        'swagger': {
            'swagger': '2.0',
            'basePath': '/api',
            'url': '/api/docs',
            'info': {
                'description': 'This is an API automatically generated by crudcast',
                'version': '1.0.0',
                'title': 'My Crudcast app'
            }
        }
    }

    models = {}

    client = None
    db = None

    def set_crudcast_config(self, config_file):
        with open(config_file, 'r') as f:
            options = load(f.read())

        for key, val in options.items():
            if key != 'models':
                self.crudcast_config[key] = val

        self.client = pymongo.MongoClient(self.crudcast_config['mongo_url'])
        self.db = self.client[self.crudcast_config['db_name']]

        for model_name, options in options['models'].items():
            m = {
                'name': model_name,
                'collection': self.db[model_name],
                'fields': options.pop('fields', []),
                'options': options
            }
            self.models[model_name] = m

    def get_tag(self, model):
        return {
            'name': model.name,
            'description': model.options.get('description')
        }

    def get_model_path(self, model):
        parameters = []

        for field in model.fields:
            parameter = {
                'name': field.name,
                'in': 'query',
                'description': 'Filter for %s objects based on %s' % (model.name, field.name),
                'required': False
            }
            parameters.append(parameter)

        post_parameters = [
            {
                'name': 'body',
                'in': 'body',
                'required': True,
                'description': 'New %s object' % model.name,
                'schema': {
                    '$ref': '#/definitions/%s' % model.name
                }
            }
        ]

        return {
            'get': {
                'tags': [model.name],
                'summary': 'List all %s objects' % model.name,
                'consumes': 'application/json',
                'produces': 'application/json',
                'parameters': parameters,
                'responses': {
                    '200': {
                        'description': 'successful operation',
                        'schema': {
                            '$ref': '#/definitions/%s' % model.name
                        }
                    }
                }
            },
            'post': {
                'tags': [model.name],
                'summary': 'Create a new %s' % model.name,
                'consumes': 'application/json',
                'produces': 'application/json',
                'parameters': post_parameters,
                'responses': {
                    '200': {
                        'description': 'object created',
                        'schema': {
                            '$ref': '#/definitions/%s' % model.name
                        }
                    }
                }
            }
        }

    def get_definition(self, model):
        definition_properties = {
            '_id': {
                'type': 'string',
            }
        }
        for field in model.fields:
            param = {
                'type': field.type
            }
            if field.type == 'array':
                param['items'] = {'type': 'string'}
            definition_properties[field.name] = param
        return {
            'type': 'object',
            'required': [field.name for field in model.fields if field.required],
            'properties': definition_properties
        }

    def get_instance_path(self, model):
        parameters = [
            {
                'name': '_id',
                'in': 'path',
                'required': True,
                'type': 'string',
                'description': 'ID of %s object' % model.name
            }
        ]
        post_parameters = [
            {
                'name': '_id',
                'in': 'path',
                'required': True,
                'type': 'string',
                'description': 'ID of %s object' % model.name
            },
            {
                'name': 'body',
                'in': 'body',
                'required': True,
                'description': 'New %s object' % model.name,
                'schema': {
                    '$ref': '#/definitions/%s' % model.name
                }
            }
        ]
        return {
            'get': {
                'tags': [model.name],
                'summary': 'Retrieve a %s object' % model.name,
                'parameters': parameters,
                'consumes': 'application/json',
                'produces': 'application/json',
                'responses': {
                    '200': {
                        'description': 'successful operation',
                        'schema': {
                            '$ref': '#/definitions/%s' % model.name
                        }
                    }
                }
            },
            'put': {
                'tags': [model.name],
                'summary': 'Update a %s object' % model.name,
                'consumes': 'application/json',
                'produces': 'application/json',
                'parameters': post_parameters,
                'responses': {
                    '200': {
                        'description': 'successful operation',
                        'schema': {
                            '$ref': '#/definitions/%s' % model.name
                        }
                    }
                }
            },
            'delete': {
                'tags': [model.name],
                'summary': 'Delete a %s object' % model.name,
                'parameters': parameters,
                'consumes': 'application/json',
                'produces': 'application/json',
                'responses': {
                    '200': {
                        'description': 'successful operation',
                        'schema': {
                            '$ref': '#/definitions/%s' % model.name
                        }
                    }
                }
            }
        }

    @property
    def swagger_config(self):
        config = self.crudcast_config['swagger']
        tags = []
        paths = {}
        definitions = {}

        for model_name, model_attrs in self.models.items():
            model = Model(model_name)
            tags.append(self.get_tag(model))
            paths['/%s/' % model_name] = self.get_model_path(model)
            paths['/%s/{_id}/' % model_name] = self.get_instance_path(model)
            definitions[model.name] = self.get_definition(model)

        config['tags'] = tags
        config['paths'] = paths
        config['definitions'] = definitions

        return config

    def get_swagger_ui_view(self):
        return get_swaggerui_blueprint(
            self.crudcast_config['swagger']['url'],
            '/swagger',
        )

    def __init__(self, import_name, config_file, **kwargs):
        self.set_crudcast_config(config_file)
        super().__init__(import_name, **kwargs)



