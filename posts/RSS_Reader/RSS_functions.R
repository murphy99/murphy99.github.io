# Get the most recent papers function

# Required Libraries

suppressPackageStartupMessages(library(tidyverse))
suppressPackageStartupMessages(library(dplyr))
library(DT)
library(tidyRSS)

most_recent_test <- function(source) {
  
  site=source
  
  my_feed_data <- tidyfeed(site) |>
    select(feed_pub_date,item_title, item_link, item_description)
  
  my_feed_data_summary <- my_feed_data |>
    select(item_title, feed_pub_date, item_link,
           item_description) 
  
  #changed item_title to item_desc
  my_rss_feed <- my_feed_data_summary |> mutate(
    item_title = str_glue("<a target='_blank' title='{item_title}' href='{item_link}' rel='noopener'>{item_title}</a>")
  )
  
  my_rss_feed_table <- my_rss_feed |> select(-item_link)
  #my_feed_data_summary
  
  
  return(my_rss_feed_table)  
}

most_recent <- function(source) {
  tryCatch({
    site <- source
    my_feed_data <- tidyfeed(site) |>
      select(feed_pub_date, item_title, item_link, item_description)
    
    my_feed_data_summary <- my_feed_data |>
      select(item_title, feed_pub_date, item_link, item_description) 
    
    my_rss_feed <- my_feed_data_summary |> mutate(
      item_title = str_glue("<a target='_blank' title='{item_title}' href='{item_link}' rel='noopener'>{item_title}</a>")
    )
    
    # Return only the most recent record
    my_rss_feed_table <- my_rss_feed |> 
      arrange(desc(feed_pub_date)) |> 
      #slice(1) |>
      select(-item_link)
    
    return(my_rss_feed_table)
  }, error = function(e) {
    message("Error fetching or parsing feed: ", e$message)
    return(NA)
  })
}




