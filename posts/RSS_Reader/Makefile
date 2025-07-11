all:	status render add commit push

status:
	git status
render: 
	/usr/local/bin/quarto render index.qmd
add:
	git add ../../docs/posts/RSS_Reader/index.html
commit:
	git commit -m "Automated RSS Feed Update"
push:
	git push origin main

.PHONY: all status render add commit push

