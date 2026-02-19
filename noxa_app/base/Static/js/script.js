// script.js

// drop down from navbar user profile
// it remains to make it disappear when the event is not taking place in it right after we show it
const dropdownMenu = document.querySelector(".dropdown-menu");
const dropdownButton = document.querySelector(".dropdown-button");

if (dropdownButton) {
  dropdownButton.addEventListener("click", () => {
    dropdownMenu.classList.toggle("show");
  });
}

// error messages, info messages and success messages handling
// We get these messages directly from django backend in pretty much any endpoint
document.querySelectorAll(".toast-message").forEach((toast) => {
  const closeBtn = toast.querySelector(".close-btn");

  // Manual close
  closeBtn.addEventListener("click", () => {
    toast.remove();
  });

  // Auto close after timeout
  const timeout = parseInt(toast.dataset.timeout, 10) || 2000;
  setTimeout(() => {
    toast.remove();
  }, timeout);
});

// Collection form modal #home.html, #publication.html and #profile.html
// Make the buttons on the form work and make sure the form only appears 
// when we click on the new collection button

// This works on three different pages the same way (#home.html, #publication.html and #profile.html)
const closeBtn = document.querySelector(".modal__header .close_btn"); // close modal
const cancelBtn = document.querySelector(".modal__btns .cancel");
const modal = document.querySelector(".modal_cont"); // the modal container

const newCollBtn = document.querySelector(".profile__container--favs__item--collections__newcol"); // new collection button

const addToCollectionBtn = document.querySelector(".add_to_collection_btn") // add to collection btn

if (modal) {
  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      modal.classList.remove("show")
    });
  }

  if (cancelBtn) {
    cancelBtn.addEventListener('click', () => {
      modal.classList.remove("show")
    });
  }

  if (newCollBtn) {
    newCollBtn.addEventListener('click', () => {
      modal.classList.toggle("show") // we switch
    });
  }

  if (addToCollectionBtn) {
    addToCollectionBtn.addEventListener('click', () => {
      modal.classList.toggle("show")
    });
  }
}


//Second modal in #publication.html: discussion creation modal form
const closeBtnDis = document.querySelector(".modal__discussion--modal__header .close_btn"); // close modal
const cancelBtnDis = document.querySelector(".modal__discussion--modal__btns .cancel");
const modalDis = document.querySelector(".modal__discussion"); // the modal container

const newDiscussionBtn = document.querySelector(".new_discussion_btn") // add to collection btn

if (modalDis) {
  if (closeBtnDis) {
    closeBtnDis.addEventListener('click', () => {
      modalDis.classList.remove("show")
    });
  }

  if (cancelBtnDis) {
    cancelBtnDis.addEventListener('click', () => {
      modalDis.classList.remove("show")
    });
  }


  if (newDiscussionBtn) {
    newDiscussionBtn.addEventListener('click', () => {
      modalDis.classList.toggle("show")
    });
  }
}




// Collection publications table #collection.html
// facilities to make the table columns resizable
document.addEventListener('DOMContentLoaded', function () {
  const createResizableTable = function (table) {
    if (!table) return;
    const cols = table.querySelectorAll('th');
    [].forEach.call(cols, function (col) {
      // Add a resizer element to the column
      const resizer = document.createElement('div')
      resizer.classList.add('resizer')

      // Set the height
      resizer.style.height = (table.offsetHeight - 3) + 'px'

      col.appendChild(resizer)

      createResizableColumn(col, resizer)
    })
  }

  const createResizableColumn = function (col, resizer) {
    let x = 0
    let w = 0

    const mouseDownHandler = function (e) {
      x = e.clientX

      const styles = window.getComputedStyle(col)
      w = parseInt(styles.width, 10)

      document.addEventListener('mousemove', mouseMoveHandler)
      document.addEventListener('mouseup', mouseUpHandler)

      resizer.classList.add('resizing')
    }

    const mouseMoveHandler = function (e) {
      const dx = e.clientX - x
      col.style.width = (w + dx) + 'px'
    }

    const mouseUpHandler = function () {
      resizer.classList.remove('resizing')
      document.removeEventListener('mousemove', mouseMoveHandler)
      document.removeEventListener('mouseup', mouseUpHandler)
    }

    resizer.addEventListener('mousedown', mouseDownHandler)
  }

  createResizableTable(document.getElementById('resizable'))
})






