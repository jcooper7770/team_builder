"""
Flask application

Endpoints:
  - /run[?league='GL|Remix|UL|ULP|ULRemix|ML|MLC']
"""

from flask import Flask, request

from team_building import get_counters_for_rating

app = Flask(__name__)


def create_table_from_results(results):
    """
    Creates an html table from the results

    :param results: The results
    :type results: str

    :return: the table for the results
    :rtype: str
    """
    table = ["<html><body style='background-color:lightgreen;'><table border='1' align='center'>"]

    for line in results.split("\n"):
        table.append("<tr>")

        # If a single value in a line then create a new table
        values = line.split("\t")
        if len(values) == 1:
            table.append("</tr></table><br><br><table border='1' align='center' style='background-color:#FFFFE0;'><tr>")
            table.append(f"<td colspan=4 align='center'>{values[0]}</td>")
        else:
            for value in values:
                if value:
                    table.extend(["<td>", value, "</td>"])

        table.append("</tr>")

    table.append("</table></html>")
    return "".join(table)


@app.route("/run")
def run():
    league = request.args.get("league", "GL")
    results = get_counters_for_rating(None, league)
    return create_table_from_results(results)

    
if __name__ == "__main__":
    app.run(debug=True)
