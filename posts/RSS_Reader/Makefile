all:	status render add commit push

status:
	git status
render: 
	/usr/local/bin/quarto render index.qmd
	/usr/local/bin/quarto render Most_Recent_Papers.qmd
add:
	git add ../../docs/posts/RSS_Reader/index.html
	git add ../../docs/posts/RSS_Reader/Most_Recent_Papers.html 
commit:
	git commit -m "Automated RSS Feed Update"
push:
	git push origin main

.PHONY: all status render add commit push

