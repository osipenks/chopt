import os
import logging
from typing import Any, Dict
from pathlib import Path
from pickledb import PickleDB


logger = logging.getLogger(__name__)


class ModelStorageChopt:

    def __init__(self, root_folder):
        root_path = os.path.join(root_folder, 'mstorage')
        if not os.path.isdir(root_path):
            os.makedirs(root_path)
        self.root = root_path

    def key_to_path(self, key: str):
        folders = key.split('.')
        prev_path = ''
        for folder in folders[:-1]:
            prev_path = os.path.join(prev_path, folder)
            folder_path = os.path.join(self.root, prev_path)
            if not os.path.isdir(folder_path):
                os.makedirs(folder_path)

        return os.path.join(self.root, prev_path, f'{folders[-1]}.json')

    def save(self, key, value):
        if not isinstance(value, dict):
            raise ValueError(f"Value must be a dictionary to save it in model storage.")
        db = PickleDB(self.key_to_path(key), False, True)
        for k, v in value.items():
            db[k] = v
        db.dump()

    def load(self, key):
        pdb = PickleDB(self.key_to_path(key), False, True)
        return pdb.db.copy()

    def updates_since(self, key, datetime):
        return True
