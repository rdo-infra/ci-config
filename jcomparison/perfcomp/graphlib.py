
import pygal
from pygal.style import Style

custom_style = Style(
  # background='transparent',
  # plot_background='transparent',
  foreground='#53E89B',
  foreground_strong='#53A0E8',
  foreground_subtle='#630C0D',
  opacity='.6',
  opacity_hover='.9',
  transition='400ms ease-in',
  colors=('#00FF80', '#E853A0')
  )


def make_bar(x, name):
    bar_chart = pygal.Bar(style=custom_style)
    bar_chart.title = 'Chart of deltas for %s' % name.capitalize()
    bar_chart.x_labels = [i[0] for i in x]
    bar_chart.add('Good', [i[1] for i in x])
    bar_chart.add('Bad', [i[2] for i in x])
    result = bar_chart.render_data_uri()
    return result
