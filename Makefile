install:
	pip install -r requirements.txt

env:
	. env/bin/activate

client: env
	python -m client

server: env
	python -m server

tests: env
	python -m tests

clean:
	rm -rf storage/
	rm -rf temp/
	rm -f server/*.pyc
	rm -f client/*.pyc
	rm -f shared/*.pyc
	rm -f tests/*.pyc
	rm -f *.log
	rm -rf __pycache__

.PHONY: install env client server tests clean
