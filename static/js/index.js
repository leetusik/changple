document.addEventListener("DOMContentLoaded", function () {
  // Get necessary elements
  const inputBox = document.querySelector(".input-box-unlocked");
  const changpleBtn = document.querySelector(".changple-btn");
  const sendBtn = document.querySelector(".send-btn");

  // Initially hide the send button
  sendBtn.style.display = "none";

  // Add input event listener to the input box
  inputBox.addEventListener("input", function () {
    // If input has text, show send button and hide changple button
    if (this.value.trim() !== "") {
      changpleBtn.style.display = "none";
      sendBtn.style.display = "flex";
    } else {
      // If input is empty, show changple button and hide send button
      changpleBtn.style.display = "flex";
      sendBtn.style.display = "none";
    }
  });
});
