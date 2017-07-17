install:
	pip install -r requirements.txt

clean:
	rm -rf storage/
	rm -f server/*.pyc
	rm -f client/*.pyc
	rm -f shared/*.pyc
	rm -f *.log
	rm -rf __pycache__

.PHONY: install clean
