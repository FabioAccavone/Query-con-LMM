import pandas as pd

result = [('2025-06-02', 8535), ('2025-06-03', 3611), ('2025-06-04', 6506), 
          ('2025-06-05', 4148), ('2025-06-06', 9575), ('2025-06-07', 9706), ('2025-06-08', 7909)]

colonne = ['day', 'steps']

df = pd.DataFrame(result, columns=colonne)

print(df)