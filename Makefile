install:
	pip install -r requirements.txt

client:
	python -m client

server:
	python -m server

tests:
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
	rm -f Server_Report_*.log

.PHONY: install client server tests clean
