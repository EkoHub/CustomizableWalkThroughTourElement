"""Test Home Assistant yaml loader."""
import io
import unittest
import os
import tempfile

from homeassistant.util import yaml


class TestYaml(unittest.TestCase):
    """Test util.yaml loader."""

    def test_simple_list(self):
        """Test simple list."""
        conf = "config:\n  - simple\n  - list"
        with io.StringIO(conf) as f:
            doc = yaml.yaml.safe_load(f)
        assert doc['config'] == ["simple", "list"]

    def test_simple_dict(self):
        """Test simple dict."""
        conf = "key: value"
        with io.StringIO(conf) as f:
            doc = yaml.yaml.safe_load(f)
        assert doc['key'] == 'value'

    def test_duplicate_key(self):
        """Test simple dict."""
        conf = "key: thing1\nkey: thing2"
        try:
            with io.StringIO(conf) as f:
                yaml.yaml.safe_load(f)
        except Exception:
            pass
        else:
            assert 0

    def test_enviroment_variable(self):
        """Test config file with enviroment variable."""
        os.environ["PASSWORD"] = "secret_password"
        conf = "password: !env_var PASSWORD"
        with io.StringIO(conf) as f:
            doc = yaml.yaml.safe_load(f)
        assert doc['password'] == "secret_password"
        del os.environ["PASSWORD"]

    def test_invalid_enviroment_variable(self):
        """Test config file with no enviroment variable sat."""
        conf = "password: !env_var PASSWORD"
        try:
            with io.StringIO(conf) as f:
                yaml.yaml.safe_load(f)
        except Exception:
            pass
        else:
            assert 0

    def test_include_yaml(self):
        """Test include yaml."""
        with tempfile.NamedTemporaryFile() as include_file:
            include_file.write(b"value")
            include_file.seek(0)
            conf = "key: !include {}".format(include_file.name)
            with io.StringIO(conf) as f:
                doc = yaml.yaml.safe_load(f)
                assert doc["key"] == "value"

    def test_include_dir_list(self):
        """Test include dir list yaml."""
        with tempfile.TemporaryDirectory() as include_dir:
            file_1 = tempfile.NamedTemporaryFile(dir=include_dir,
                                                 suffix=".yaml", delete=False)
            file_1.write(b"one")
            file_1.close()
            file_2 = tempfile.NamedTemporaryFile(dir=include_dir,
                                                 suffix=".yaml", delete=False)
            file_2.write(b"two")
            file_2.close()
            conf = "key: !include_dir_list {}".format(include_dir)
            with io.StringIO(conf) as f:
                doc = yaml.yaml.safe_load(f)
                assert sorted(doc["key"]) == sorted(["one", "two"])

    def test_include_dir_named(self):
        """Test include dir named yaml."""
        with tempfile.TemporaryDirectory() as include_dir:
            file_1 = tempfile.NamedTemporaryFile(dir=include_dir,
                                                 suffix=".yaml", delete=False)
            file_1.write(b"one")
            file_1.close()
            file_2 = tempfile.NamedTemporaryFile(dir=include_dir,
                                                 suffix=".yaml", delete=False)
            file_2.write(b"two")
            file_2.close()
            conf = "key: !include_dir_named {}".format(include_dir)
            correct = {}
            correct[os.path.splitext(os.path.basename(file_1.name))[0]] = "one"
            correct[os.path.splitext(os.path.basename(file_2.name))[0]] = "two"
            with io.StringIO(conf) as f:
                doc = yaml.yaml.safe_load(f)
                assert doc["key"] == correct

    def test_include_dir_merge_list(self):
        """Test include dir merge list yaml."""
        with tempfile.TemporaryDirectory() as include_dir:
            file_1 = tempfile.NamedTemporaryFile(dir=include_dir,
                                                 suffix=".yaml", delete=False)
            file_1.write(b"- one")
            file_1.close()
            file_2 = tempfile.NamedTemporaryFile(dir=include_dir,
                                                 suffix=".yaml", delete=False)
            file_2.write(b"- two\n- three")
            file_2.close()
            conf = "key: !include_dir_merge_list {}".format(include_dir)
            with io.StringIO(conf) as f:
                doc = yaml.yaml.safe_load(f)
                assert sorted(doc["key"]) == sorted(["one", "two", "three"])

    def test_include_dir_merge_named(self):
        """Test include dir merge named yaml."""
        with tempfile.TemporaryDirectory() as include_dir:
            file_1 = tempfile.NamedTemporaryFile(dir=include_dir,
                                                 suffix=".yaml", delete=False)
            file_1.write(b"key1: one")
            file_1.close()
            file_2 = tempfile.NamedTemporaryFile(dir=include_dir,
                                                 suffix=".yaml", delete=False)
            file_2.write(b"key2: two\nkey3: three")
            file_2.close()
            conf = "key: !include_dir_merge_named {}".format(include_dir)
            with io.StringIO(conf) as f:
                doc = yaml.yaml.safe_load(f)
                assert doc["key"] == {
                    "key1": "one",
                    "key2": "two",
                    "key3": "three"
                }
