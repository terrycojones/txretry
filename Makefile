.PHONY: test wc pep8 pyflakes clean _upload _register

test:
	trial txretry

wc:
	find txretry -name '*.py' -print0 | xargs -r -0 wc -l

pep8:
	find txretry -name '*.py' -print0 | xargs -r -0 -n 1 pep8 --repeat

pyflakes:
	find txretry -name '*.py' -print0 | xargs -r -0 pyflakes

clean:
	find . \( -name '*.pyc' -o -name '*~' \) -print0 | xargs -r -0 rm 
	find . -type d -name _trial_temp -print0 | xargs -r -0 rm -r
	rm -fr MANIFEST dist

# Normal users will not need to make _upload.
_upload:
	python setup.py sdist upload

# Normal users will not need to make _register.
_register:
	python setup.py register
