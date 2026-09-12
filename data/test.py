import pandas as pd

movies = pd.read_csv("data/ml-latest-small/movies.csv")

print(movies.head())
print(movies.columns)
print(movies.shape) 
movies.info()
print(movies["title"].head())
scifi_movies = movies[movies["genres"].str.contains("Sci-Fi")]

print(scifi_movies.head())
print(movies.isnull().sum())
print(movies.describe(include="all"))
