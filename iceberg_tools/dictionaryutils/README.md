This package was cloned from [dictionaryutils](https://github.com/uc-cdis/dictionaryutils/tree/master/dictionaryutils)
It was cloned to remove dependency gen3
The gen3 sdk depends on dictionaryutils which depends on gen3datamodel which has a dependency on a very old version of jsonschema.
We would consider forking it and submitting a PR, however the gen3datamodel component doesn’t seem to be in the UChicago git repository?
