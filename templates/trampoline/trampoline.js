var curr_page = 1;
var paginated_practices = [];
$(document).ready(function() {
    // Set logger date to current local date if a search date isn't chosen
    {% if not search_date %}
    {% if not current_date %}
    var date = new Date();
    date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
    document.getElementById("logger-date").value = date.toJSON().slice(0,10);
    document.getElementById("airtime-date").value = date.toJSON().slice(0,10);
    {% else %}
    document.getElementById("logger-date").value = "{{current_date}}";
    document.getElementById("airtime-date").value = "{{current_date}}";
    document.getElementById("practice_date").value = "{{current_date}}";
    {% endif %}
    {% else %}
    document.getElementById("logger-date").value = "{{search_date}}";
    document.getElementById("airtime-date").value = "{{search_date}}";
    document.getElementById("practice_date").value = "{{search_date}}";
    {% endif %}

    // paginate practices
    var practices = [];
    var practices_div = document.getElementById("practices");
    var nodes = practices_div.childNodes;
    for (element of nodes){
        if (element.tagName == "DIV") {
            practices.push(element);
        }
    }

    var page_size = 10;
    n_pages = Math.floor(practices.length / page_size) + 1;
    for(i=0; i< n_pages; i++) {
        var start = i * page_size;
        var end = (i+1) * page_size;
        if(end > practices.length) {
            end = practices.length;
        }
        var current_page = practices.slice(start, end);
        paginated_practices.push(current_page);
    }

    practices_div.innerHTML = "";

    var page_buttons = document.createElement("div");
    page_buttons.id = "page_buttons";
    page_buttons.classList.add("text-center")

    var next_page = document.createElement("button");
    next_page.innerHTML = "Next >>";
    next_page.style = "padding:0 10px; curdor: pointer;"
    next_page.id = "page_next";
    next_page.onclick = changePage;
    //practices_div.prepend(next_page);
    page_buttons.prepend(next_page);
    for(page=paginated_practices.length; page>0; page--){
        var new_page = document.createElement("button")
        new_page.innerHTML = page;
        new_page.id = "page_"+page;
        new_page.onclick = changePage;
        new_page.style = "padding:0 10px; curdor: pointer;"
        //practices_div.prepend(new_page)
        page_buttons.prepend(new_page)
    }
    var prev_page = document.createElement("button");
    prev_page.innerHTML = "<< Prev";
    prev_page.style = "padding:0 10px; curdor: pointer;"
    prev_page.id = "page_prev";
    prev_page.onclick = changePage;
    //practices_div.prepend(prev_page);
    page_buttons.prepend(prev_page);
    practices_div.append(page_buttons);

    var practices_page = document.createElement("div");
    practices_page.id = "practices_page";
    for(element of paginated_practices[curr_page-1]){
        practices_page.append(element);
        practices_page.append(document.createElement("br"));
        practices_page.append(document.createElement("br"));
    }
    practices_div.append(practices_page);

});

// Change the practice page
const changePage = function() {
    var page_id = this.id;
    var page = this.id.split("_")[1];
    if (page == curr_page){
        return
    }
    if(page == "prev"){
        if(curr_page > 1) {
            page = curr_page - 1;
        } else {
            return
        }
    }
    if(page == "next"){
        if(curr_page<paginated_practices.length){
            page = curr_page + 1;
        } else {
            return
        }
    }
    curr_page_id = "page_"+curr_page;
    document.getElementById(curr_page_id).style.background = "#FFFFFF";
    
    curr_page = parseInt(page);
    curr_page_id = "page_"+curr_page;
    document.getElementById(curr_page_id).style.background = "#0000FF";
    var practices_page = document.getElementById("practices_page");
    practices_page.innerHTML = "";
    for(element of paginated_practices[curr_page-1]){
        practices_page.append(element);
        practices_page.append(document.createElement("br"));
        practices_page.append(document.createElement("br"));
    }

}
// keep the skill dropdowns open
$(function() {
    $("div.dropdown-menu").on("click", "[data-keepopenonclick]", function(e) {
            e.stopPropagation();
    });
});
// unhide the hidden notes by clicking the comment button
$("[id^=unhide-note").click(function(e){
    var comment = $(this).siblings('span')[0];
    if (comment.style.display === "none") {
        comment.style.display = "inline";
    } else {
        comment.style.display = "none";
    }
});
$("[id^=skill]").click(function (e) {
    e.preventDefault();
    var skill = event.target.id.slice(5).replace('t', 'o').replace('p', '<').replace('s', '/');
    console.log("adding " + skill);
    var routineText = document.getElementById('log').value;
    if (routineText != "") {
        $('#log').val(routineText + ' ' + skill);
    } else {
        $('#log').val(skill);
    }
});

$("#col-skill").on('click', 'a', function (e) {
    e.preventDefault();
    var skill = event.target.id.slice(5).replace('t', 'o').replace('p', '<').replace('s', '/');
    console.log("adding " + skill);
    var routineText = document.getElementById('log').value;
    if (routineText != "") {
        $('#log').val(routineText + ' ' + skill);
    } else {
        $('#log').val(skill);
    }
    addRecSkill();
});
function updateNumSkills() {
    let skills = $("#log").val().trim().split(/[\s]/);
    let num_skills = skills.length;
    document.getElementById('num_skills').textContent = "Number of skills: " + num_skills;
}
function addRecSkill() {
    var skill_text = $("#log").val();
    // ignore if last skill was a space
    if (skill_text[skill_text.length - 1] == " ") {
        return
    }
    let skills = skill_text.split(/[\s]/);
    var last_skill = skills[skills.length - 1];
    var next_skill = recommendSkill(last_skill);
    if (next_skill != undefined && next_skill != "") {
        // clear out all recommended 
        var recc = document.getElementsByClassName("recc-skill");
        while(recc.length > 0) {
            recc[0].parentNode.removeChild(recc[0]);
        }

        // add new recommended
        console.log("recommended: " + next_skill);
        // add a button with the skill under the log
        var new_line = document.createElement("br");
        new_line.className = "recc-skill";
        for(let i=0; i<next_skill.length; i++){
            n_skill = next_skill[i];
            var new_link = document.createElement('a');
            new_link.id = "skill" + n_skill;
            new_link.value = "skill" + n_skill;
            new_link.textContent = n_skill;
            new_link.className = "recc-skill"
            new_link.style = "display: inline-block; width: auto; border: 1px solid; background-color: #F5F5F5; margin-right: 10px";
            logger = document.getElementById("log");
            logger.parentNode.insertBefore(new_link, logger.nextSibling);
        }
        logger.parentNode.insertBefore(new_line, logger.nextSibling);

        // automatically add to log
        //$('#log').val(skill_text + ' ' + next_skill);
    }
}

function recommendSkill(current_skill) {
    //var all_turns = JSON.parse('{{ user_turns | tojson }}');
    var all_turns = {{ user_turns | tojson }};
    var next_skills = {};
    for (let turn_num = 0; turn_num < all_turns.length; turn_num++) {
        var turn = all_turns[turn_num];
        skill = "";
        for (let skill_num = 0; skill_num < turn.length - 1; skill_num++) {
            var skill = turn[skill_num];
            //console.log("Current: " + current_skill + " - checking " + skill);
            // Get next skill if the current skill was found
            if (skill == current_skill){
                next_skill = turn[skill_num + 1];
                if (!(next_skill in next_skills)) {
                    next_skills[next_skill] = 0;
                }
                next_skills[next_skill]++;
            }
        }
    }

    if (next_skills.length == 0) {
        return "";
    }

    // sort and find the most used next skill
    var items = Object.keys(next_skills).map(function(key) {
        return [key, next_skills[key]];
    });
    items.sort(function(first, second) {
        return second[1] - first[1];
    });
    if (items.length == 0) {
        return "";
    }
    console.log(next_skills);
    most_used_next = items[0][0];
    most_used_next = items.slice(0, 5);
    most_used = []
    for (let i=0; i<most_used_next.length; i++){
        most_used.push(most_used_next[i][0]);
    }
    return most_used;

};

$("#log").on('input', function (e) {
    //updateNumSkills();
    addRecSkill();
});
$("[id$=_skills]").change(function (e) {
    var skill = $(this).val().slice(5).replace('t', 'o').replace('p', '<').replace('s', '/');
    var routineText = document.getElementById('log').value;
    if (routineText != "") {
        $('#log').val(routineText + ' ' + skill);
    } else {
        $('#log').val(skill);
    }
    //updateNumSkills();
});
$('[id^=copy-text]').click(function(e){
    // Add copy of text to log
    var tds = e.target.parentNode.parentNode.parentNode.children;
    var routine = "";
    for (var i=0; i<tds.length; i++){
        var td = tds[i];
        if (td.firstChild == null){
            break;
        }    
        else {
            if (td.firstChild.tagName == undefined){
                var doc = new DOMParser().parseFromString(td.innerHTML, "text/html");
                var elementText = doc.documentElement.textContent;
                routine = routine + " " + elementText;
            }
        }
    }
    var skills = document.getElementById('log').value;
    var newText = "";
    if (skills != ""){
        newText = skills + '\n' + routine;
    } else {
        newText = routine;
    }
    
    // Remove extra spaces
    newText = newText.trim().replace('\n ', '\n');
    $('#log').val(newText);
});
$('#repeat-skills').click(function (e) {
    //var skills = $('log').val();
    var skills = document.getElementById('log').value;
    if (skills != "") {
        if (skills.endsWith('\n')) {
            var newText = skills + skills;
        } else {
            var newText = skills + ' ' + skills;
        }
        nextText = newText.trim().replace('\n ', '\n');
        $('#log').val(newText);
    }
    $('#log').focus();
});
$('#next-line').click(function(e) {
    var skills = document.getElementById('log').value;
    if (skills != "" && !skills.endsWith('\n')) {
        $('#log').val(skills + '\n');
    }
    $('#log').focus();
});
$("[id^=minimize_]").click(function(e){
    var section_to_minimize = event.target.id.split("_")[1];
    var minimize_id = section_to_minimize + "_body";
    var x = document.getElementById(minimize_id);
    if (x.style.display === "none") {
        x.style.display = "";
    } else {
        x.style.display = "none";
    }
    var button = document.getElementById(e.target.id);
    if (button.className == "fa fa-window-minimize") {
        button.className = "fa fa-window-maximize";
    } else {
        button.className = "fa fa-window-minimize";
    }
});
$("[id^=remove_]").click(function (e) {
    e.preventDefault();
    var date_to_remove = event.target.id.split("_")[1];
    var event_to_remove = event.target.id.split("_")[2];
    let confirmText = "".concat("Are you sure you want to delete ", date_to_remove, " ", event_to_remove, "?");
    if (confirm(confirmText) == true) {
        $.ajax({
            type: 'GET',
            url: "/logger/delete/" + date_to_remove + "/" + event_to_remove,
            success: function (data) {
                location.reload();
            }
        });
    }
});