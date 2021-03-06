class ContentBase(object):

    field_map = {}

    admin_field_map = {}

    sub_resources = []

    recent_endpoint = None
    alpha_endpoint = None
    count_endpoint = None

    def __init__(self, **kwargs):

        # Make all of the keyword arguments attributes of this instance
        self.__dict__.update(kwargs)

    @classmethod
    def get_field_names(cls, include_resources=False,
                        include_admin_fields=False):
        field_names = list(cls.field_map.keys())
        if include_resources:
            field_names += cls.sub_resources
        if include_admin_fields:
            field_names += list(cls.admin_field_map.keys())
        return field_names

    @classmethod
    def from_json_dict(cls, json_dict):

        field_dict = {}

        for (k, v) in list(json_dict.items()):
            map_result = cls.field_map.get(k, k)

            if type(map_result) is tuple:
                new_name, val_func = map_result
                new_value = val_func(v)
            else:
                new_name = map_result
                new_value = v

            field_dict[new_name.encode('ascii')] = new_value

        # Map the JSON property names to this names used in this class
        # field_dict = dict((cls.field_map.get(k, k), v) for (k, v) \
        #                 in json_dict.items())

        return cls(**field_dict)
