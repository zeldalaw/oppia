# coding: utf-8
#
# Copyright 2014 The Oppia Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Domain objects for configuration properties."""

from core.platform import models
import feconf
import schema_utils

(config_models,) = models.Registry.import_models([models.NAMES.config])
memcache_services = models.Registry.import_memcache_services()

CMD_CHANGE_PROPERTY_VALUE = 'change_property_value'

SET_OF_STRINGS_SCHEMA = {
    'type': 'list',
    'items': {
        'type': 'unicode',
    },
    'validators': [{
        'id': 'is_uniquified',
    }],
}

VMID_SHARED_SECRET_KEY_SCHEMA = {
    'type': 'list',
    'items': {
        'type': 'dict',
        'properties': [{
            'name': 'vm_id',
            'schema': {
                'type': 'unicode'
            }
        }, {
            'name': 'shared_secret_key',
            'schema': {
                'type': 'unicode'
            }
        }]
    }
}

BOOL_SCHEMA = {
    'type': schema_utils.SCHEMA_TYPE_BOOL
}

UNICODE_SCHEMA = {
    'type': schema_utils.SCHEMA_TYPE_UNICODE
}


class ConfigProperty(object):
    """A property with a name and a default value.

    NOTE TO DEVELOPERS: These config properties are deprecated. Do not reuse
    these names:
    - about_page_youtube_video_id
    - admin_email_address
    - admin_ids
    - admin_usernames
    - allow_yaml_file_upload
    - banned_usernames
    - banner_alt_text
    - before_end_body_tag_hook
    - carousel_slides_config
    - collection_editor_whitelist
    - contact_email_address
    - contribute_gallery_page_announcement
    - disabled_explorations
    - editor_page_announcement
    - editor_prerequisites_agreement
    - embedded_google_group_url
    - full_site_url
    - moderator_ids
    - moderator_request_forum_url
    - moderator_usernames
    - publicize_exploration_email_html_body
    - sharing_options
    - sharing_options_twitter_text
    - sidebar_menu_additional_links
    - site_forum_url
    - social_media_buttons
    - splash_page_exploration_id
    - splash_page_exploration_version
    - splash_page_youtube_video_id
    - ssl_challenge_responses
    - whitelisted_email_senders
    """

    def refresh_default_value(self, default_value):
        pass

    def __init__(self, name, schema, description, default_value):
        if Registry.get_config_property(name):
            raise Exception('Property with name %s already exists' % name)

        self._name = name
        self._schema = schema
        self._description = description
        self._default_value = schema_utils.normalize_against_schema(
            default_value, self._schema)

        Registry.init_config_property(self.name, self)

    @property
    def name(self):
        return self._name

    @property
    def schema(self):
        return self._schema

    @property
    def description(self):
        return self._description

    @property
    def default_value(self):
        return self._default_value

    @property
    def value(self):
        """Get the latest value from memcache, datastore, or use default."""

        memcached_items = memcache_services.get_multi([self.name])
        if self.name in memcached_items:
            return memcached_items[self.name]

        datastore_item = config_models.ConfigPropertyModel.get(
            self.name, strict=False)
        if datastore_item is not None:
            memcache_services.set_multi({
                datastore_item.id: datastore_item.value})
            return datastore_item.value

        return self.default_value

    def set_value(self, committer_id, raw_value):
        """Sets the value of the property. In general, this should not be
        called directly -- use config_services.set_property() instead.
        """
        value = self.normalize(raw_value)

        # Set value in datastore.
        model_instance = config_models.ConfigPropertyModel.get(
            self.name, strict=False)
        if model_instance is None:
            model_instance = config_models.ConfigPropertyModel(
                id=self.name)
        model_instance.value = value
        model_instance.commit(committer_id, [{
            'cmd': CMD_CHANGE_PROPERTY_VALUE,
            'new_value': value
        }])

        # Set value in memcache.
        memcache_services.set_multi({
            model_instance.id: model_instance.value})

    def normalize(self, value):
        return schema_utils.normalize_against_schema(value, self._schema)


class Registry(object):
    """Registry of all configuration properties."""

    # The keys of _config_registry are the property names, and the values are
    # ConfigProperty instances.
    _config_registry = {}

    @classmethod
    def init_config_property(cls, name, instance):
        cls._config_registry[name] = instance

    @classmethod
    def get_config_property(cls, name):
        return cls._config_registry.get(name)

    @classmethod
    def get_config_property_schemas(cls):
        """Return a dict of editable config property schemas.

        The keys of the dict are config property names. The values are dicts
        with the following keys: schema, description, value.
        """
        schemas_dict = {}

        for (property_name, instance) in cls._config_registry.iteritems():
            schemas_dict[property_name] = {
                'schema': instance.schema,
                'description': instance.description,
                'value': instance.value
            }

        return schemas_dict


PROMO_BAR_ENABLED = ConfigProperty(
    'promo_bar_enabled', BOOL_SCHEMA,
    'Whether the promo bar should be enabled for all users', False)
PROMO_BAR_MESSAGE = ConfigProperty(
    'promo_bar_message', UNICODE_SCHEMA,
    'The message to show to all users if the promo bar is enabled', '')

VMID_SHARED_SECRET_KEY_MAPPING = ConfigProperty(
    'vmid_shared_secret_key_mapping', VMID_SHARED_SECRET_KEY_SCHEMA,
    'VMID and shared secret key corresponding to that VM',
    [{
        'vm_id': feconf.DEFAULT_VM_ID,
        'shared_secret_key': feconf.DEFAULT_VM_SHARED_SECRET
    }])
