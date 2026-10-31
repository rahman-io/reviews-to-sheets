import pandas as pd


def summary(reviews):
    """One row per product: number of reviews, average rating, how many of each star and the worst review."""
    df = pd.DataFrame(reviews)
    rows = []
    for product, group in df.groupby('product'):
        worst = group.sort_values(['rating', 'date']).iloc[0]
        row = {
            'Product': product,
            'Reviews': len(group),
            'Avg rating': round(group['rating'].mean(), 2),
        }
        for stars in range(5, 0, -1):
            row[f'{stars} star' + ('s' if stars > 1 else '')] = int((group['rating'] == stars).sum())
        row['Latest review'] = group['date'].max()
        row['Lowest rated'] = f"{worst['rating']}/5: {worst['text']}"
        rows.append(row)
    return pd.DataFrame(rows).sort_values(['Avg rating', 'Reviews'], ascending=False, ignore_index=True)


def save_csv(out_dir, reviews, testimonials, summary_df):
    out_dir.mkdir(parents=True, exist_ok=True)
    # utf-8-sig so Excel opens the csv with the right characters
    pd.DataFrame(reviews).to_csv(out_dir / 'reviews.csv', index=False, encoding='utf-8-sig')
    pd.DataFrame(testimonials).to_csv(out_dir / 'testimonials.csv', index=False, encoding='utf-8-sig')
    summary_df.to_csv(out_dir / 'summary.csv', index=False, encoding='utf-8-sig')
