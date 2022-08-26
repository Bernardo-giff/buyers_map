import dash
import dash_html_components as html
from simple_salesforce import Salesforce
import dash_core_components as dcc
from dash.dependencies import Input, Output
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import geopy.distance
from functions import *

##-------------------GET DATA FROM SALESFORCE--------------------------------------------------------------------

accounts = get_salesforce_table('queries/accounts_query')
materials = get_salesforce_table('queries/materials_query')
orders = get_salesforce_table('queries/orders_query')
cart = get_salesforce_table('queries/cart_query')

#--------------------DEFINE COLUMNS THAT ARE GOING TO BE DROPPED OR RENAMED IN FINAL DF ------------------------

columns_to_drop = ['Material__c', 'Order__c', 'Id_x', 'Id_y', 'SellerRef__c', 
                   'BuyerRef__c', 'IsBuyer__c_seller', 'IsSeller__c_seller', 
                   'IsBuyer__c_buyer', 'IsSeller__c_buyer', 'Id_buyer', 'Id_seller']

columns_to_rename = {"Name_x": "material", "Name_y": "seller", 'Margin__c':'margin',
                     'QuantitiyPurchase__c':'weight', 'TotalPricePurchase__c':'cost', 'TotalPriceSell__c':'sale',
                     'Category__c':'category', "Segment__c_seller": "segment_seller", "BillingLatitude_seller":'seller_lat',
                     "BillingLongitude_seller":'seller_lon', "BillingLatitude_buyer":'buyer_lat', "BillingLongitude_buyer":'buyer_lon',
                     "Segment__c_buyer": "segment_buyer", 'Name':'buyer'}

#-------------------MAKE TRANSFORMATIONS TO CART TO GET THE FINAL DF----------------------------------------------

cart = cart.merge(materials, left_on='Material__c', right_on='Id')
cart = cart.merge(orders, left_on='Order__c', right_on='Id')
cart = cart.merge(accounts, left_on='SellerRef__c', right_on='Id')
cart = cart.merge(accounts, left_on='BuyerRef__c', right_on='Id', suffixes=['_seller', '_buyer'])
cart.drop(columns_to_drop, axis=1, inplace=True)
cart.rename(columns=columns_to_rename, inplace=True)
cart['seller_coor'] = list(zip(cart.seller_lat, cart.seller_lon))
cart['buyer_coor'] = list(zip(cart.buyer_lat, cart.buyer_lon))

#-------------------DEFINE INITIAL VALUES FOR THE DASH----------------------------------------------------------
sellers = list(cart['seller'][cart['buyer_lat'].notna()].unique())
categories = list(materials['Category__c'].unique())
materials_list = []

#-------------------DEFINE STYLE COMPONENTS----------------------------------------------------------------------

tile_style = {'backgroundColor':'transparent', 
              'padding-left':3, 'padding-right':3, 'padding-bottom':10, 'padding-top':10, 
              'border':'2px solid #E7EFF8', 'border-radius': '15px 15px 15px 15px'}
header_style = {'textAlign':'center','color':'#E7EFF8'}
app = dash.Dash()
server = app.server

app.layout = html.Div([
                html.Div([
                        html.Div([html.H2(children='Seller',style=header_style),
                                  dcc.Dropdown(sellers, id='seller_dropdown', value='Schrottwolf GmbH')],style=tile_style),
                        html.Div([html.H2(children='Category',style=header_style),
                                  dcc.Dropdown(categories, id='category_dropdown', value='Kupfer')],style=tile_style),
                        html.Div([html.H2(children='Material',style=header_style),
                                  dcc.Dropdown(materials_list, id='material_dropdown', disabled=True)],style=tile_style),
                        html.Div([html.H2(children='Distance',style=header_style),
                                  dcc.Slider(
                                        id='distance_slider',
                                        min=0,
                                        max=3000,
                                        value=200,
                                        step=None
                                    )],style=tile_style),
                        html.Div(id='text',style=tile_style)],style={'width':'25%', 'height': '100%', 'padding':3}),
                html.Div([
                        html.Div(dcc.Graph(id='map_plot')),
                      ],style={'width':'85%', 'height': '100%', 'padding':3})
                ],style={'display':'flex', 
                             'background-image': 'url(https://schrott24--c.documentforce.com/sfc/dist/version/renditionDownload?rendition=ORIGINAL_Png&versionId=0680900000DuuED&operationContext=DELIVERY&contentId=05T0900000jaipy&page=0&d=/a/090000005JTy/0XKJQ7sXrJrOoUvKcB4SLEEFg1Q3Va5kJvjVAOl3.f0&oid=00D09000001K0B2&dpt=null&viewId=)',                             
                             'background-size': '100%'})



@app.callback(
    [Output('material_dropdown', 'options'),
     Output('material_dropdown', 'disabled')],
    Input('category_dropdown', 'value'))

def update_material_dropdown(category_dropdown):
    materials_list = list(materials.loc[materials['Category__c']==category_dropdown]['Name'])

    return materials_list, category_dropdown is None

@app.callback(Output("loading-output-1", "children"), Input("map_plot", "data-dash-is-loading"))
def input_triggers_spinner(value):
    return value

@app.callback(
    [Output('map_plot', 'figure'),
     Output('text','children')],
    [Input('seller_dropdown', 'value'),
     Input('distance_slider', 'value'),
     Input('category_dropdown', 'value'),
     Input('material_dropdown', 'value')]
)
def update_output(seller_dropdown, distance_slider, category_dropdown, material_dropdown):
    global cart
    seller = seller_dropdown
    distance = distance_slider
    category = category_dropdown
    material = material_dropdown
    selected_seller = cart.loc[cart['seller']==seller].iloc[0]
    seller_lon = selected_seller[9]
    seller_lat = selected_seller[8]
    buyers_df = cart[['buyer','buyer_coor', 'buyer_lat', 'buyer_lon', 'weight', 'category', 'material']][cart['buyer_lat'].notna()]
    buyers_df['distance'] = buyers_df['buyer_coor'].apply(lambda row: geopy.distance.geodesic(row, (seller_lat,seller_lon)).km)

    if seller is None and category is None:
        group = buyers_df.groupby(by=['buyer', 'category']).agg({'buyer_lat':'max', 
                                                            'buyer_lon':'max', 
                                                            'weight':'sum',
                                                            'distance':'max'}) 
        buyers_df = group.reset_index()
    elif seller is not None and material is None:
        group = buyers_df.groupby(by=['buyer', 'category']).agg({'buyer_lat':'max', 
                                                            'buyer_lon':'max', 
                                                            'weight':'sum',
                                                            'distance':'max'}) 
        buyers_df = group.reset_index()
        buyers_df = buyers_df[(buyers_df['distance']<=distance) & (buyers_df['category']==category)]
    else:
        group = buyers_df.groupby(by=['buyer', 'material']).agg({'buyer_lat':'max', 
                                                            'buyer_lon':'max', 
                                                            'weight':'sum',
                                                            'distance':'max'}) 
        buyers_df = group.reset_index()
        buyers_df = buyers_df[(buyers_df['distance']<=distance) & (buyers_df['material']==material)]
        
    fig = px.scatter_mapbox(buyers_df,
                            lon = 'buyer_lon',
                            lat = 'buyer_lat',
                            text='buyer',
                            size='weight',
                            zoom=5.5,
                            width=1000,
                            height=700,
                            title='Buyers')

    fig.update_layout(mapbox_style='open-street-map')

    text = """
              The Map is showing buyers of {}, in a radius of {} km of {}""".format(category, distance, seller)
    return fig, text

if __name__ == '__main__':
    app.run_server()