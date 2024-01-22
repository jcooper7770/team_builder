var curr_page = 1;
var paginated_practices = [];
$(document).ready(function() {
    // Set logger date to current local date if a search date isn't chosen
    {% if url_for(request.endpoint) == "/logger" or request.endpoint == "coach.coach_home" %}
    {% if not search_date %}
    {% if not current_date %}
    var date = new Date();
    date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
    document.getElementById("logger-date").value = date.toJSON().slice(0,10);
    {% if request.endpoint != "coach.coach_home" %}
    document.getElementById("airtime-date").value = date.toJSON().slice(0,10);
    {% endif %}
    {% else %}
    document.getElementById("logger-date").value = "{{current_date}}";
    {% if request.endpoint != "coach.coach_home" %}
    document.getElementById("airtime-date").value = "{{current_date}}";
    document.getElementById("practice_date").value = "{{current_date}}";
    {% endif %}
    {% endif %}
    {% else %}
    document.getElementById("logger-date").value = "{{search_date}}";
    {% if request.endpoint != "coach.coach_home" %}
    document.getElementById("airtime-date").value = "{{search_date}}";
    document.getElementById("practice_date").value = "{{search_date}}";
    {% endif %}
    {% endif %}
    {% endif %}
    paginate();
});

const paginate = function() {
    // paginate practices
    var practices = [];
    var practices_div = document.getElementById("practices");
    var nodes = practices_div.childNodes;
    for (element of nodes){
        if (element.tagName == "DIV") {
            practices.push(element);
        }
    }

    // split practices into pages
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

    // clear the practices div
    practices_div.innerHTML = "";

    // create buttons for pages
    createPageButtons();

    // create practice page divs
    var practices_page = document.createElement("div");
    practices_page.id = "practices_page";
    for(element of paginated_practices[curr_page-1]){
        practices_page.append(element);
        practices_page.append(document.createElement("br"));
        practices_page.append(document.createElement("br"));
    }
    practices_div.append(practices_page);

}

const createPageButtons = function () {
    // clear the practices div
    var practices_div = document.getElementById("practices");
    practices_div.innerHTML = "";
    // create buttons for pages
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

}

const repaginate = function() {
    var newPaginatedPractices = [];

    var numCurrentPage = 0; // number of non-hidden on page
    var paginatedPage = []; // current page of elements
    for(page=0; page < paginated_practices.length; page++){
        for (element of paginated_practices[page]) {
            paginatedPage.push(element);
            if (element.firstChild.style.display != "none") {
                numCurrentPage++;
            }

            // start a new page if there are 10 non-hidden things
            if (numCurrentPage == 10) {
                newPaginatedPractices.push(paginatedPage);
                //console.log("Starting a new page");
                //console.log(paginatedPage);
                paginatedPage = [];
                numCurrentPage = 0;
            }
        }
    }
    newPaginatedPractices.push(paginatedPage);

    paginated_practices = newPaginatedPractices;
    createPageButtons();
    //var practices_page = document.getElementById("practices_page");
    //practices_page.innerHTML = "";
    var practices_page = document.createElement("div");
    practices_page.id = "practices_page";
    curr_page = 1;
    //console.log(paginated_practices);
    for(element of paginated_practices[curr_page-1]){
        practices_page.append(element);
        if (element.firstChild.style.display != "none") {
            practices_page.append(document.createElement("br"));
            practices_page.append(document.createElement("br"));
        }
    }
    var practices_div = document.getElementById("practices");
    practices_div.appendChild(practices_page);

}

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
        if (element.firstChild.style.display != "none") {
            practices_page.append(document.createElement("br"));
            practices_page.append(document.createElement("br"));
        }
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
    console.log(event.target.id)
    if (event.target.id == "new-turn-button") {
        return
    }
    var skill = event.target.id.slice(5).replace('t', 'o').replace('p', '<').replace('s', '/');
    console.log("adding " + skill);
    // type into last log
    const logElements = document.querySelectorAll("#log");
    const logElement = logElements[logElements.length-2];
    if (document.activeElement.id == "log") {
        logElement = document.activeElement;
    }

    //var routineText = document.getElementById('log').value;
    var routineText = logElement.value;
    if (routineText != "") {
        //$('#log').val(routineText + ' ' + skill);
        logElement.value = routineText + ' ' + skill;
    } else {
        //$('#log').val(skill);
        logElement.value = skill;
    }
    // Set log height to fit text inside
    if (logElement.scrollHeight > logElement.offsetHeight) {
        logElement.style.height = `${logElement.scrollHeight}px`;
    }
    addRecSkill();
});

$("#col-skill").on('click', 'a', function (e) {
    e.preventDefault();
    if (event.target.parentNode.className.startsWith("remove-log") || event.target.parentNode.id.startsWith("new-turn-button")) {
        return;
    }
    if (event.target.id == "new-turn-button"){
        return
    }
    var skill = event.target.id.slice(5).replace('t', 'o').replace('p', '<').replace('s', '/');
    console.log("adding " + skill);
    // type into last log
    const logElements = document.querySelectorAll("#log");
    const logElement = logElements[logElements.length-2];
    if (document.activeElement.id == "log") {
        logElement = document.activeElement;
    }

    //var routineText = document.getElementById('log').value;
    var routineText = logElement.value;
    if (routineText != "") {
        logElement.value = routineText + ' ' + skill;
        //$('#log').val(routineText + ' ' + skill);
    } else {
        logElement.value = skill;
        //$('#log').val(skill);
    }
    // Set log height to fit text inside
    if (logElement.scrollHeight > logElement.offsetHeight) {
        logElement.style.height = `${logElement.scrollHeight}px`;
    }
    addRecSkill();
});
function updateNumSkills() {
    let skills = $("#log").val().trim().split(/[\s]/);
    let num_skills = skills.length;
    document.getElementById('num_skills').textContent = "Number of skills: " + num_skills;
}
function clearRecs() {
    var recc = document.getElementsByClassName("recc-skill");
    while(recc.length > 0) {
        recc[0].parentNode.removeChild(recc[0]);
    }
}
function addRecSkill() {
    //var skill_text = $("#log").val();
    const logElements = document.querySelectorAll("#log");
    const logElement = logElements[logElements.length-2];
    console.log(logElement.value);
    var skill_text = logElement.value;
    // ignore if last skill was a space
    if (skill_text[skill_text.length - 1] == " ") {
        return
    }
    let skills = skill_text.split(/[\s]/);
    var last_skill = skills[skills.length - 1];
    var next_skill = recommendSkill(last_skill);
    if (next_skill != undefined && next_skill != "") {
        // clear out all recommended
        clearRecs() 
        /*
        var recc = document.getElementsByClassName("recc-skill");
        while(recc.length > 0) {
            recc[0].parentNode.removeChild(recc[0]);
        }
        */

        var bottom = document.getElementById("logger-bottom")
        // add new recommended
        console.log("recommended: " + next_skill);
        // add a button with the skill under the log
        for(let i=0; i<next_skill.length; i++){
            n_skill = next_skill[i];
            var new_link = document.createElement('a');
            new_link.id = "skill" + n_skill;
            new_link.value = "skill" + n_skill;
            new_link.textContent = n_skill;
            new_link.className = "recc-skill btn btn-info"
            bottom.appendChild(new_link);
        }

        // automatically add to log
        //$('#log').val(skill_text + ' ' + next_skill);
    }
}

function recommendSkill(current_skill) {
    if ( {{ user_turns }} == undefined) {
        var all_turns = [];
    }else {
        var all_turns = {{ user_turns | tojson }};
    }
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

//$("#log").on('input', function (e) {
$("#new-turns").on('input', '#log', function (e) {
    //updateNumSkills();
    addRecSkill();

    // Set log height to fit text inside
    if (e.target.scrollHeight > e.target.offsetHeight) {
        e.target.style.height = `${e.target.scrollHeight}px`;
    }
});

// Get a reference to the button and spinner elements
const button = document.getElementById("submit-button");
const spinner = document.querySelector(".spinner-container");
if (button != null) {
    button.addEventListener("click", function() {
    showSpinner("Submitting data...")
    });
}
const goal_button = document.getElementById("submit-goals")
if (goal_button != null) {
    goal_button.addEventListener("click", function() {
    showSpinner("Submitting goals...")
    });
}

const airtime_button = document.getElementById("submit-airtime")
if (airtime_button != null) {
    airtime_button.addEventListener("click", function() {
    showSpinner("Submitting airtime...")
    });
}
const skill_button = document.getElementById("submit-skills")
if (skill_button != null) {
    skill_button.addEventListener("click", function() {
        showSpinner("Submitting skill for search...")
    });
}
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
        if (td == undefined || td.children.length == 0) {
        //if (td == undefined || td.firstChild == null){
            break;
        }    
        else {
            for(var j=1; j<td.children.length; j++) {
                if (td.children[j].innerText != "") {
                    routine = routine + " " + td.innerText;
                }
            }
            /*
            if (td.firstChild.tagName == undefined){
                var doc = new DOMParser().parseFromString(td.innerHTML, "text/html");
                var elementText = doc.documentElement.textContent;
                routine = routine + " " + elementText;
            }
            */
        }
    }
    const logElements = document.querySelectorAll("#log");
    const logElement = logElements[logElements.length-2];
    var skills = logElement.value;
    var newText = "";
    if (skills != ""){
        newText = skills + '\n' + routine;
    } else {
        newText = routine;
    }
    
    // Remove extra spaces
    newText = newText.trim().replace('\n ', '\n');
    //$('#log').val(newText);
    logElement.value = newText;
});
$('#repeat-skills').click(function (e) {
    //var skills = $('log').val();
    const logElements = document.querySelectorAll("#log");
    const logElement = logElements[logElements.length-2];
    var skills = logElement.value;
    if (skills != "") {
        if (skills.endsWith('\n')) {
            var newText = skills + skills;
        } else {
            var newText = skills + ' ' + skills;
        }
        nextText = newText.trim().replace('\n ', '\n');
        //$('#log').val(newText);
        logElement.value = newText;
    }
    //$('#log').focus();
    logElement.focus();
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
$("[id^=edit_]").click(function (e) {
    var date_to_edit = event.target.id.split("_")[1];
    var event_to_edit = event.target.id.split("_")[2];
    let confirmText = "".concat("Are you sure you want to edit ", date_to_edit, " ", event_to_edit, "?");
    if (confirm(confirmText) == true) {
        var url = "/logger/edit/" + date_to_edit + "/" + event_to_edit;
        location.href = encodeURI(url);
    }
});
$("[id^=remove_]").click(function (e) {
    e.preventDefault();
    var date_to_remove = event.target.id.split("_")[1];
    var event_to_remove = event.target.id.split("_")[2];
    let confirmText = "".concat("Are you sure you want to delete ", date_to_remove, " ", event_to_remove, "?");
    if (confirm(confirmText) == true) {
        showSpinner("Deleting data...")

        $.ajax({
            type: 'GET',
            url: "/logger/delete/" + date_to_remove + "/" + event_to_remove,
            success: function (data) {
                location.reload();
            }
        });
    }
});

//
// Rating dropdown
//
// Get the dropdown menu template
const dropdownTemplate = document.querySelector('#dropdown-template');

// Function to add the dropdown menu to a table header
function addDropdownToTableHeader(tableHeader) {
  // Clone the dropdown template content
  const dropdown = dropdownTemplate.content.cloneNode(true);

  // Append the dropdown menu to the table header
  tableHeader.appendChild(dropdown);
}

// Add post button
function addPostToTableHeader(header) {
    const button = document.createElement("button");
    button.classList = "btn btn-primary color-changing";
    button.innerText = "Post To Feed"
    button.addEventListener("click", function(e) {
        e.preventDefault();
        const name = e.target.parentNode.parentNode.parentNode.getAttribute("name");
        console.log(e.target.parentNode.parentNode.nextSibling);
        const tagDivs = e.target.parentNode.parentNode.nextSibling.childNodes;
        const tags = [];
        tagDivs.forEach((div) => {
            tags.push(div.innerText);
        })
        console.log(tagDivs);
        console.log(tags);
        const data = {practice: name, tags: tags}
        $.ajax({
            type: 'POST',
            url: "/logger/practice/post",
            contentType: 'application/json',
            data: JSON.stringify(data),
            success: function (data) {
                console.log("successfully saved data");
                alert("Post successful");
            }
        });
    });
    header.appendChild(button);
}

// Get all table headers and add the dropdown menu to each one
const tableHeaders = document.querySelectorAll('#practice-header');
tableHeaders.forEach(function (header) {
  addDropdownToTableHeader(header);

  // add post option also
  addPostToTableHeader(header);
});

// Event delegation for dynamically added rating options
document.addEventListener('click', function (event) {
  const target = event.target;
  if (target.classList.contains('rating-option')) {
    handleRatingSelection(target);
  }
});

// Event delegation for dynamically added dropdown buttons
document.addEventListener('click', function (event) {
  const target = event.target;
  if (target.classList.contains('dropdown-btn')) {
    const dropdownContent = target.nextElementSibling;
    dropdownContent.style.display =
      dropdownContent.style.display === 'block' ? 'none' : 'block';
  }
});

// Function to handle rating option selection
function handleRatingSelection(option) {
  const selectedRating = option.textContent;
  const rating = option.getAttribute("name");

  // Perform any desired action with the selected rating
  console.log('Selected rating:', selectedRating);
  option.parentNode.parentNode.parentNode.firstChild.textContent = selectedRating;
  option.parentNode.parentNode.parentNode.firstChild.setAttribute("name", rating);

  var practice_name = option.parentNode.parentNode.parentNode.parentNode.parentNode.getAttribute("name")
  // save the rating by sending a POST
  const data = {rating: rating, date: practice_name}
  $.ajax({
    type: 'POST',
    url: "/logger/rate_practice",
    contentType: 'application/json',
    data: JSON.stringify(data),
    success: function (data) {
        console.log("successfully saved data");
    }
  });

}

$("[id^=search-rating]").click(function(e) {
    // remove all backgrounds of search buttons
    document.querySelectorAll("[id^=search-rating]").forEach(x => {
        x.style.background = "";
    });
    const rating = e.target.id.slice(-1);
    e.target.style.background = "blue";
    showSpinner("Searching by rating...");

    for(let i=0; i<paginated_practices.length; i++) {
        var page = paginated_practices[i];
        for (let j=0; j<page.length; j++) {
            var container = page[j];
            var table = container.children[0];

            // re-display the table incase it was hidden
            table.style.display = "";
            if (rating == "0") {
                continue
            }
            var thead = table.children[0];
            var table_rating_element = thead.children[0].children[0].firstChild.firstChild.firstChild;
            const table_rating = table_rating_element.getAttribute("name");
            if (table_rating != rating) {
                table.style.display = "none";
            }

        }
    }
    document.querySelector('.spinner-container').style.display = "none";

});

//$("[class^=remove-log]").click(function(e){
$("#new-turns").on('click', '.remove-log', function(e){
    e.preventDefault();
    var parentDiv = e.target.parentNode;  
    if (e.target.tagName == "I") {
        parentDiv = e.target.parentNode.parentNode;
    }
    console.log(parentDiv);
    const allTurnsDiv = document.getElementById("new-turns");
    allTurnsDiv.removeChild(parentDiv);
    const skillsDiv = document.getElementById("col-skill");
    addRecSkill();

});

$("#new-turns").on('click', '.copy-log-button', function(e){
    e.preventDefault();
    var inputDiv = e.target.parentNode;
    if (e.target.tagName == "I") {
        inputDiv = e.target.parentNode.parentNode;
    }
    const value = inputDiv.children[2].value;
    const newLogDiv = createNewLog(e, value);
    const allTurnsDiv = document.getElementById("new-turns");
    //inputDiv.after(newLogDiv);
    allTurnsDiv.children[allTurnsDiv.children.length-3].after(newLogDiv);

});


function createNewLog(e, value) {
    const logTurnDivs = document.querySelectorAll("[id^=log-turn]");

    var newDiv = document.createElement("div");
    newDiv.id = `log-turn-${logTurnDivs.length-1}`;

    var removeButton = document.createElement("a");
    removeButton.classList = "remove-log color-changing";
    removeButton.href = "#";
    removeButton.innerHTML = '<i class="fa fa-minus-square" aria-hidden="true"></i>';
    var copyButton = document.createElement("a");
    copyButton.classList = "copy-log-button color-changing";
    copyButton.href = "#";
    copyButton.innerHTML = '<i class="fa fa-clone" aria-hidden="true"></i>';
    if(localStorage.getItem("theme") == "dark-mode"){
        removeButton.classList.add("dark-mode-color");
        copyButton.classList.add('dark-mode-color');
    }
    newDiv.appendChild(removeButton);
    newDiv.appendChild(copyButton);

    var inputDiv = e.target.parentNode;
    if (e.target.tagName == "I") {
        inputDiv = e.target.parentNode.parentNode;
    }
    const newInput = document.createElement("textarea");
    newInput.style.border = '0';
    newInput.id = "log";
    newInput.style.width = "100%";
    newInput.style.height = "30px";
    newInput.classList = "color-changing";
    newInput.placeholder = "Input your turn here...";
    newInput.value = value;
    newInput.name = `log-${logTurnDivs.length-1}`;
    if(localStorage.getItem("theme") == "dark-mode"){
        newInput.classList.add("dark-mode-color");
    }
    newDiv.appendChild(newInput);
    return newDiv;
   
}

$("[id^=new-turn-button]").click(function(e) {
    const newDiv = createNewLog(e, "");
    const allTurnsDiv = document.getElementById("new-turns");
    var inputDiv = e.target.parentNode;
    if (e.target.tagName == "I") {
        inputDiv = e.target.parentNode.parentNode;
    }
    allTurnsDiv.insertBefore(newDiv, inputDiv);

    clearRecs();
});

$("[id^=search-tag]").click(function(e) {
    document.querySelectorAll("[id^=search-tag]").forEach(x => {
        x.style.background = "";
    });
    const tag = e.target.textContent;
    e.target.style.background = "blue";
    showSpinner("Searching by tag...");

    for(let i=0; i<paginated_practices.length; i++) {
        var page = paginated_practices[i];
        for (let j=0; j<page.length; j++) {
            var container = page[j];
            var table = container.children[0];

            // re-display the table incase it was hidden
            table.style.display = "";
            if (tag == "Reset") {
                continue
            }
            var thead = table.children[0];
            var table_tag_elements = thead.children[0].children[0].children[1];
            const table_tags = table_tag_elements.textContent;
            if (!table_tags.includes(tag)) {
                table.style.display = "none";
            }

        }
    }
    document.querySelector('.spinner-container').style.display = "none";

});


$("#search-practice").click(function (e) {
    showSpinner("Searching for date");
    var val = document.querySelector("#practice_date").value;
    console.log(val);
    if (val == null | val == "") {
        $.ajax({
            type: 'GET',
            url: "/logger/search?practice_date=",
            success: function (data) {
                location.reload();
            }
        });
        return
    }
    var date = new Date(val);
    var string_date = ((date.getMonth() > 8) ? (date.getMonth() + 1) : ('0' + (date.getMonth() + 1))) + '/' + ((date.getDate() > 8) ? (date.getDate()+1) : ('0' + (date.getDate()+1))) + '/' + date.getFullYear();
    console.log(string_date);
    for(let i=0; i<paginated_practices.length; i++) {
        var page = paginated_practices[i];
        for (let j=0; j<page.length; j++) {
            var container = page[j];
            var table = container.children[0];

            // re-display the table incase it was hidden
            table.style.display = "";
            if (val == "" || val == null) {
                continue
            }
            var thead = table.children[0];
            var title = thead.children[0].children[0].innerHTML;
            if (!title.includes(string_date)) {
                table.style.display = "none";
            }
        }
    }
    document.querySelector('.spinner-container').style.display = "none";
});

function showSpinner(text) {
  var spinnerText = document.querySelector('.spinner-text');
  var textContent = text || "Loading...";
  spinnerText.textContent = textContent;

  // add css for each letter to cause a delay
  var spanCount = textContent.length;
  var spanCSS = "";
  for (var i = 1; i <= spanCount; i++) {
    var delay = (i - 1) * 0.1;
    spanCSS += `.spinner-text span:nth-child(${i}) { animation-delay: ${delay}s; } `;
  }
  var styleElement = document.querySelector("style[type='text/css']");
  styleElement.insertAdjacentHTML('beforeend', spanCSS);

  // move each letter into a span element
  var chars = text.split('');
  var wrappedChars = chars.map(function(char) {
    return '<span>' + char + '</span>';
  });
  spinnerText.innerHTML = wrappedChars.join('');

  // make the spinner visible
  var spinnerContainer = document.querySelector(".spinner-container");
  spinnerContainer.style.display = "flex";

  // allow spinner to be closed
  var spinnerClose = document.getElementById("spinner-close");
  spinnerClose.addEventListener("click", function() {
    spinnerContainer.style.display = "none";
  });
}

function scrollToSection(event, sectionId) {
    event.preventDefault(); // Prevent the default anchor behavior
    var section = document.getElementById(sectionId);
    if (section) {
        var offset = 0; // Adjust this value based on your fixed navbar height
        var sectionPosition = section.getBoundingClientRect().top + window.scrollY;
        window.scrollTo({
            top: sectionPosition - offset,
            behavior: 'smooth'
        });
    }
}

var logSubmitBtn = document.getElementById("logger");
function handleSubmitBtn() {
    // Get the selected tags
    var selectedTags = Array.from(document.querySelectorAll('.tag-box.selected'))
                          .map(function(tagBox) {
                              return tagBox.textContent;
                          });

    // Set the selected tags in the hidden input field
    var tagInput = document.getElementById('selected-tags');
    tagInput.value = selectedTags.join(',');
    console.log(tagInput.value);
}
logSubmitBtn.addEventListener('submit', handleSubmitBtn);

// Function to toggle full-screen mode
function toggleFullScreen() {
    var notepad = document.querySelector('#col-skill');
    var textarea = document.getElementById('log');
    const fullScreenSubmitButton = document.getElementById("submit-button-full-screen");

    notepad.classList.toggle('full-screen');
    textarea.classList.toggle('full-screen');

    if (notepad.classList.contains("full-screen")) {
        fullScreenSubmitButton.style.display = "";
    } else {
        fullScreenSubmitButton.style.display = "none";
    }
}

// Attach functions to the corresponding events
document.getElementById('fullScreenBtn').addEventListener('click', toggleFullScreen);

// expand the turn to get into
$('[class^="expand-turn"]').click(function (e) {
    const turnDetailsDiv = e.target.parentNode.lastElementChild;
    if (turnDetailsDiv.style.display == "none") {
        turnDetailsDiv.style.display = "";
        //e.target.classList = "expand-tab fa fa-caret-up";
        e.target.classList = "expand-tab fa fa-minus";
    } else {
        e.target.classList = "expand-tab fa fa-plus";
        turnDetailsDiv.style.display = "none";
    }
});

// Add in lesson plans
var lessonPlansObj = [
    {% for lesson in lesson_plans %}
    { title: "{{lesson.title}}", description: `{{lesson.description}}`, date: "{{lesson.date}}", plans: {{ lesson.plans | safe }}, finished: {{ lesson.athletes_completed | safe }} },
    {% endfor %}
]
lessonPlansObj.forEach((lesson) => {
    addSingleLesson(lesson.title, lesson.description, lesson.date, lesson.plans, lesson.finished);
})

function addSingleLesson(title, description, date, plans, finished) {
// Display the lesson plan using Bootstrap alert
const lessonPlansDiv = document.getElementById('lessonPlans');
const newLessonPlanDiv = document.createElement('div');
newLessonPlanDiv.classList.add('alert', 'alert-success');

//<ul>${plans.map(plan => `<li style="list-style: none;"><input type="checkbox" style="margin-right: 5px;"\>${plan}</li>`).join('')}</ul>

var inputs = [];
{% if request.endpoint != "coach.coach_home" %}
for (let i=0; i<plans.length; i++) {
    const plan = plans[i];
    var checked = "";
    if (finished.{{user}}.includes(plan)) {
        checked = " checked";
    }
    inputs.push(`<li style="list-style: none;"><input${checked} type="checkbox" style="margin-right: 5px;" \>${plan}</li>`);
}
{% else %}
for (let i=0; i<plans.length; i++) {
    const plan = plans[i];
    var finishedAthletes = [];
    for (const [key, value] of Object.entries(finished)) {
        if (value.includes(plan)) {
            finishedAthletes.push(key);
        }
    }
    inputs.push(`<li>${plan} (${finishedAthletes.join(', ')})</li>`);
}
{% endif %}
newLessonPlanDiv.innerHTML = `<div class="lesson-plan">
<div class="lesson-plan-header">
    <strong>${title}</strong>
    <div class="action-btns">
        {% if request.endpoint == "coach.coach_home" %}
        <button class="btn btn-warning btn-sm" onclick="editLessonPlan(this)"><i class="fa fa-pencil-square-o" aria-hidden="true"></i></button>
        <button class="btn btn-warning btn-sm" onclick="deleteLesson(this)"><i class="fa fa-trash-o" aria-hidden="true"></i></button>
        {% endif %}
    </div>
</div>
<p>Date: ${date}</p>
<p><i>${description.replace(/\n/g, '<br>')}</i></p>
<p><u>Plans</u></p>

{% if request.endpoint == "coach.coach_home" %}
<ul>${inputs.join(' ')}</ul>
{% else %}
<ul>${inputs.join(' ')}</ul>
<button class="btn btn-primary ml-auto" id="save-lesson">Save</button>
{% endif %}
</div>
<hr>`;
lessonPlansDiv.appendChild(newLessonPlanDiv);
}

$("[id^=save-lesson]").click(function (e) {
    e.preventDefault();

    // Get all checboxes that are checked
    var checkedTurns = [];
    const listElements = e.target.parentNode.children[4].children;
    for(let i=0; i<listElements.length; i++){
        const listElement = listElements[i];
        if (listElement.children[0].checked) {
            checkedTurns.push(listElement.textContent);
        }
    }
    console.log(checkedTurns);

    // Save
    const data = {
        finishedTurns: checkedTurns,
        name: "{{ user }}",
        title: e.target.parentNode.querySelector("strong").textContent,
        date: e.target.parentNode.children[1].textContent.replace("Date: ", "")
    }
    console.log(data);
    $.ajax({
        type: 'POST',
        url: "/logger/lessons/complete",
        contentType: 'application/json',
        data: JSON.stringify(data),
        success: function (data) {
            console.log("successfully saved data");
            alert("Post successful");
        }
    });

});