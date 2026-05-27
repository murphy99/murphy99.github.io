Then render with:

# Development (cache only)
quarto render index.qmd -P dev_mode:true

# Production (API enabled)
quarto render index.qmd -P dev_mode:false
