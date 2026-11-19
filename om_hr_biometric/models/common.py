def group_records(records, key):
    """ :return: {key value: records} of `records` grouped by `key` (a field name or a function), in their order """
    groups = {}
    for record in records:
        value = record[key] if isinstance(key, str) else key(record)
        groups[value] = groups.get(value, records.browse()) | record
    return groups
