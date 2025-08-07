all:	render_LLM_Demo  render_RSS_Reader  render_Shinylive 
weekend: render_LLM_Demo render_Shiny2

render_LLM_Demo: 
	/usr/local/bin/quarto render posts/LLM_Demo/index.qmd	
render_RSS_Reader: 
	/usr/local/bin/quarto render posts/RSS_feeds/index.qmd
	/usr/local/bin/quarto render posts/RSS_feeds/Most_Recent_Papers.qmd
render_Shiny2:
	/usr/local/bin/quarto render posts/Shinylive/index.qmd
render_Shinylive: 
	/usr/local/bin/quarto add quarto-ext/shinylive
	/usr/local/bin/Rscript -e 'update.packages("shinylive")'
	/usr/local/bin/quarto render posts/Shinylive/index.qmd  

.PHONY: all render_LLM_Demo  render_RSS_Reader  render_Shinylive   
