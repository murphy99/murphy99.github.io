library(shiny)

ui <- fluidPage(
  titlePanel("Histogram of mtcars$mpg"),
  sidebarLayout(
    sidebarPanel(
      sliderInput("bins", "Number of bins:", min = 5, max = 30, value = 10)
    ),
    mainPanel(
      plotOutput("histPlot")
    )
  )
)

server <- function(input, output, session) {
  output$histPlot <- renderPlot({
    hist(mtcars$mpg, breaks = input$bins, col = "skyblue", border = "white")
  })
}

shinyApp(ui, server)
