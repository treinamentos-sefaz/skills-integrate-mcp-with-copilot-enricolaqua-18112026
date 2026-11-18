document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const signupContainer = document.getElementById("signup-container");
  const messageDiv = document.getElementById("message");
  const accountButton = document.getElementById("account-button");
  const accountActions = document.getElementById("account-actions");
  const openLogin = document.getElementById("open-login");
  const logoutButton = document.getElementById("logout");
  const loginDialog = document.getElementById("login-dialog");
  const loginForm = document.getElementById("login-form");
  const loginError = document.getElementById("login-error");
  let authenticated = false;

  function showMessage(message, success) {
    messageDiv.textContent = message;
    messageDiv.className = success ? "success" : "error";
  }

  function updateAccount() {
    signupContainer.classList.toggle("hidden", !authenticated);
    openLogin.classList.toggle("hidden", authenticated);
    logoutButton.classList.toggle("hidden", !authenticated);
  }

  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      if (!response.ok) throw new Error("Unable to load activities");
      const activities = await response.json();
      activitiesList.replaceChildren();
      activitySelect.replaceChildren(new Option("-- Select an activity --", ""));

      Object.entries(activities).forEach(([name, details]) => {
        const card = document.createElement("div");
        card.className = "activity-card";
        const heading = document.createElement("h4");
        heading.textContent = name;
        card.appendChild(heading);
        for (const text of [
          details.description,
          `Schedule: ${details.schedule}`,
          `Availability: ${details.max_participants - details.participants.length} spots left`,
        ]) {
          const paragraph = document.createElement("p");
          paragraph.textContent = text;
          card.appendChild(paragraph);
        }
        const participants = document.createElement("div");
        participants.className = "participants-container";
        if (details.participants.length === 0) {
          participants.textContent = "No participants yet";
        } else {
          const title = document.createElement("h5");
          title.textContent = "Participants:";
          const list = document.createElement("ul");
          list.className = "participants-list";
          details.participants.forEach((email) => {
            const item = document.createElement("li");
            const label = document.createElement("span");
            label.className = "participant-email";
            label.textContent = email;
            item.appendChild(label);
            if (authenticated) {
              const remove = document.createElement("button");
              remove.className = "delete-btn";
              remove.type = "button";
              remove.textContent = "❌";
              remove.setAttribute("aria-label", `Remove ${email}`);
              remove.addEventListener("click", () => unregister(name, email));
              item.appendChild(remove);
            }
            list.appendChild(item);
          });
          participants.classList.add("participants-section");
          participants.append(title, list);
        }
        card.appendChild(participants);
        activitiesList.appendChild(card);
        activitySelect.add(new Option(name, name));
      });
    } catch (error) {
      activitiesList.textContent = "Failed to load activities. Please try again later.";
      console.error("Error fetching activities:", error);
    }
  }

  async function changeRegistration(url, method) {
    try {
      const response = await fetch(url, { method });
      const result = await response.json();
      if (response.status === 401) {
        authenticated = false;
        updateAccount();
        await fetchActivities();
        alert("Your session expired. Please log in again.");
      } else {
        showMessage(result.message || result.detail, response.ok);
        if (response.ok) await fetchActivities();
      }
    } catch (error) {
      showMessage("Request failed. Please try again.", false);
      console.error("Error updating registration:", error);
    }
  }

  function unregister(activity, email) {
    return changeRegistration(
      `/activities/${encodeURIComponent(activity)}/unregister?email=${encodeURIComponent(email)}`,
      "DELETE"
    );
  }

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const email = document.getElementById("email").value;
    const activity = activitySelect.value;
    await changeRegistration(
      `/activities/${encodeURIComponent(activity)}/signup?email=${encodeURIComponent(email)}`,
      "POST"
    );
  });

  accountButton.addEventListener("click", () => {
    const expanded = accountActions.classList.toggle("hidden") === false;
    accountButton.setAttribute("aria-expanded", String(expanded));
  });
  openLogin.addEventListener("click", () => {
    loginError.classList.add("hidden");
    loginDialog.showModal();
  });
  document.getElementById("cancel-login").addEventListener("click", () => loginDialog.close());
  loginDialog.addEventListener("close", () => loginForm.reset());

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: document.getElementById("username").value,
          password: document.getElementById("password").value,
        }),
      });
      const result = await response.json();
      if (!response.ok) {
        loginError.textContent = result.detail;
        loginError.classList.remove("hidden");
        return;
      }
      authenticated = true;
      updateAccount();
      loginDialog.close();
      await fetchActivities();
    } catch (error) {
      loginError.textContent = "Login failed. Please try again.";
      loginError.classList.remove("hidden");
      console.error("Login failed:", error);
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      const response = await fetch("/auth/logout", { method: "POST" });
      if (!response.ok && response.status !== 401) throw new Error("Logout failed");
      authenticated = false;
      updateAccount();
      await fetchActivities();
    } catch (error) {
      alert("Logout failed. Please try again.");
      console.error("Logout failed:", error);
    }
  });

  async function initialize() {
    try {
      const response = await fetch("/auth/session");
      if (!response.ok) throw new Error("Unable to check session");
      authenticated = (await response.json()).authenticated;
    } catch (error) {
      const accountError = document.getElementById("account-error");
      accountError.textContent = "Could not check login status. Please reload the page.";
      accountError.classList.remove("hidden");
      console.error("Unable to check session:", error);
    }
    updateAccount();
    await fetchActivities();
  }
  initialize();
});
