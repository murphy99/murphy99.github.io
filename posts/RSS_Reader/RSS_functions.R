# Get the most recent papers function

most_recent <- function(source) {
  
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
  
  
  return(my_rss_feed_table)  # Explicit return is optional, but good practice
  
}