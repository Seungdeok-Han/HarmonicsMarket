// view_post.js - 댓글, 답글, 좋아요, 브랜드 툴팁 등 모든 인터랙션 담당

document.addEventListener("DOMContentLoaded", function () {
  // 댓글 엔터 등록
  const form = document.getElementById("comment-form");
  const textarea = document.getElementById("comment-content");
  if (form && textarea) {
    textarea.addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        form.dispatchEvent(new Event("submit", {cancelable: true, bubbles: true}));
      }
    });
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      const content = textarea.value.trim();
      if (!content) return;
      fetch(form.dataset.url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest"
        },
        credentials: "include",
        body: JSON.stringify({ content: content })
      })
        .then(res => res.json())
        .then(function(data) {
          if (data.success) {
            textarea.value = "";
            appendComment(data);
          }
        })
        .catch(function(err) { alert("댓글 오류: " + err); });
    });
  }

  // 답글 작성, 댓글 삭제, 답글 엔터 등록 등은 comment-list가 있을 때만 바인딩
  const commentList = document.getElementById("comment-list");
  if (commentList) {
    commentList.addEventListener("click", function (e) {
      if (e.target && e.target.classList.contains("reply-submit")) {
        const button = e.target;
        const input = button.closest(".reply-form").querySelector(".reply-input");
        const content = input.value.trim();
        const parentId = input.getAttribute("data-parent-id");
        if (!content) return;
        fetch(form.dataset.url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest"
          },
          credentials: "include",
          body: JSON.stringify({ content: content, parent_id: parentId })
        })
          .then(res => res.json())
          .then(data => {
            if (data.success) {
              const replyList = document.getElementById(`reply-list-${parentId}`);
              const replyDiv = document.createElement("div");
              replyDiv.className = "mt-3 ms-4 border-start ps-3";
              replyDiv.id = `comment-${data.comment_id}`;
              replyDiv.innerHTML = `
  <strong>${data.username}</strong>
  <small class="text-muted">(${data.timestamp})</small>
  ${data.can_delete ? `<button class="btn btn-sm btn-outline-danger float-end delete-comment" data-comment-id="${data.comment_id}">삭제</button>` : ""}
  <br>${data.content}
`;
              replyList.appendChild(replyDiv);
              input.value = "";
              const form = document.getElementById(`reply-form-${parentId}`);
              if (form) form.style.display = "none";
            }
          })
          .catch(err => console.error("답글 오류:", err));
      }
    });

    commentList.addEventListener("click", function (e) {
      if (e.target && e.target.classList.contains("delete-comment")) {
        const commentId = e.target.getAttribute("data-comment-id");
        const confirmed = confirm("정말로 이 댓글을 삭제하시겠습니까?");
        if (!confirmed) return;
        fetch(`/comments/${commentId}/delete`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest"
          },
          credentials: "include"
        })
          .then(res => res.json())
          .then((data) => {
            if (data.success) {
              const commentElem = document.getElementById(`comment-${commentId}`);
              if (commentElem) {
                commentElem.remove();
              }
            } else {
              alert("삭제 권한이 없거나 실패했습니다.");
            }
          })
          .catch(err => {
            console.error("삭제 요청 중 오류:", err);
            alert("서버 오류로 인해 삭제할 수 없습니다.");
          });
      }
    });

    commentList.addEventListener("keydown", function (event) {
      if (
        event.target.classList.contains("reply-input") &&
        event.key === "Enter" &&
        !event.shiftKey
      ) {
        event.preventDefault();
        // 답글 작성 버튼 클릭 이벤트 트리거
        const replyForm = event.target.closest(".reply-form");
        if (replyForm) {
          const submitBtn = replyForm.querySelector(".reply-submit");
          if (submitBtn) submitBtn.click();
        }
      }
    });
  }

  // 좋아요 버튼
  const likeBtn = document.getElementById("like-button");
  if (likeBtn) {
    likeBtn.addEventListener("click", function () {
      fetch(likeBtn.dataset.url, {
        method: "POST",
        headers: { "X-Requested-With": "XMLHttpRequest" },
        credentials: "include"
      })
      .then(res => res.json())
      .then(data => {
        if (data.liked !== undefined) {
          likeBtn.innerHTML = data.liked ? "❤️ 좋아요 취소" : "🤍 좋아요";
          document.getElementById("like-count").innerText = data.like_count + "명이 좋아합니다";
        }
      });
    });
  }

  // 브랜드 툴팁 안전하게 이벤트 바인딩
  document.querySelectorAll('.brand-tooltip-trigger').forEach(function(elem) {
    elem.addEventListener('mouseover', function(event) {
      window.showTooltip(event, 'brand', elem.getAttribute('data-brand-id'));
    });
    elem.addEventListener('mouseout', function(event) {
      window.hideTooltip();
    });
  });

  // 쉐입 툴팁 이벤트 바인딩
  document.querySelectorAll('.shape-tooltip-trigger').forEach(function(elem) {
    elem.addEventListener('mouseover', function(event) {
      window.showShapeTooltip(event, elem.getAttribute('data-shape'));
    });
    elem.addEventListener('mouseout', function(event) {
      window.hideTooltip();
    });
  });

  // 시세 그래프 폼 이벤트
  const priceForm = document.getElementById("price-history-form");
  if (priceForm) {
    priceForm.addEventListener("submit", function (e) {
      e.preventDefault();
      const brandId = document.getElementById("brand-select").value;
      const modelName = document.getElementById("model-select").value.trim();
      if (!brandId || !modelName) return;
      fetch(`/api/price_history?brand_id=${brandId}&model_name=${encodeURIComponent(modelName)}`)
        .then(res => res.json())
        .then(data => {
          console.log('시세 그래프 응답:', data); // 콘솔 출력 추가
          const chartDiv = document.getElementById("price-history-chart");
          if (data.labels && data.labels.length > 0) {
            chartDiv.style.display = "block";
            drawPriceChart(data.labels, data.prices);
          } else {
            chartDiv.style.display = "block";
            chartDiv.innerHTML = '<div class="text-muted">최근 거래 데이터가 없습니다.</div>';
          }
        });
    });
  }

  // 시세 그래프 영역: 브랜드 선택 시 모델명 자동완성 (view_post.js로 이동)
  const brandSelect = document.getElementById('brand-select');
  const modelInput = document.getElementById('model-select');
  const modelList = document.getElementById('model-list');
  if (brandSelect && modelInput && modelList) {
    brandSelect.addEventListener('change', function() {
      const brandId = brandSelect.value;
      const brandName = brandSelect.options[brandSelect.selectedIndex]?.text;
      if (brandId && brandName) {
        fetch(`/api/models_by_brand?brand=${encodeURIComponent(brandName)}`)
          .then(res => res.json())
          .then(data => {
            modelList.innerHTML = '';
            (data.models || []).forEach(model => {
              if (model && typeof model === 'string' && model.trim().length > 1) {
                const option = document.createElement('option');
                option.value = model;
                modelList.appendChild(option);
              }
            });
          });
      } else {
        modelList.innerHTML = '';
      }
    });
  }
});

function appendComment(data) {
  const commentList = document.getElementById("comment-list");
  const li = document.createElement("li");
  li.className = "list-group-item";
  li.id = `comment-${data.comment_id}`;
  const strong = document.createElement("strong");
  strong.textContent = data.username;
  const small = document.createElement("small");
  small.className = "text-muted";
  small.textContent = `(${data.timestamp})`;
  li.appendChild(strong);
  li.appendChild(small);
  if (data.can_delete) {
    const delBtn = document.createElement("button");
    delBtn.className = "btn btn-sm btn-outline-danger float-end delete-comment";
    delBtn.setAttribute("data-comment-id", data.comment_id);
    delBtn.textContent = "삭제";
    li.appendChild(delBtn);
  }
  li.appendChild(document.createElement("br"));
  li.appendChild(document.createTextNode(data.content));
  const div = document.createElement("div");
  div.className = "mt-2";
  const replyA = document.createElement("a");
  replyA.href = "javascript:void(0);";
  replyA.innerHTML = "&#8618; 답글";
  replyA.onclick = function() { window.toggleReplyForm(data.comment_id); };
  div.appendChild(replyA);
  const replyForm = document.createElement("form");
  replyForm.id = `reply-form-${data.comment_id}`;
  replyForm.className = "reply-form mt-2";
  replyForm.style.display = "none";
  const inputGroup = document.createElement("div");
  inputGroup.className = "input-group";
  const input = document.createElement("input");
  input.type = "text";
  input.className = "form-control reply-input";
  input.placeholder = "답글을 입력하세요";
  input.setAttribute("data-parent-id", data.comment_id);
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "btn btn-sm btn-outline-primary reply-submit";
  btn.textContent = "작성";
  inputGroup.appendChild(input);
  inputGroup.appendChild(btn);
  replyForm.appendChild(inputGroup);
  div.appendChild(replyForm);
  li.appendChild(div);
  const replyList = document.createElement("div");
  replyList.id = `reply-list-${data.comment_id}`;
  li.appendChild(replyList);
  commentList.appendChild(li);
}

function toggleReplyForm(commentId) {
  const form = document.getElementById(`reply-form-${commentId}`);
  if (form) {
    form.style.display = form.style.display === "none" ? "block" : "none";
  }
}

function showTooltip(event, category, id) {
    id = parseInt(id, 10);
    fetch(`/api/info/${category}/${id}`)
        .then(function(res) { return res.json(); })
        .then(function(data) {
            tooltip = document.getElementById('infoTooltip');
            if (data.error) {
                tooltip.innerHTML = '<strong>정보를 불러올 수 없습니다.</strong>';
            } else {
                tooltip.innerHTML = `<strong>${data.title}</strong><br>${data.description}`;
            }
            tooltip.style.display = 'block';
            tooltip.style.left = event.pageX + 10 + 'px';
            tooltip.style.top = event.pageY + 10 + 'px';
        })
        .catch(function() {
            tooltip = document.getElementById('infoTooltip');
            tooltip.innerHTML = '<strong>정보를 불러올 수 없습니다.</strong>';
            tooltip.style.display = 'block';
            tooltip.style.left = event.pageX + 10 + 'px';
            tooltip.style.top = event.pageY + 10 + 'px';
        });
}
function hideTooltip() {
    if (tooltip) tooltip.style.display = 'none';
}
window.showTooltip = showTooltip;
window.hideTooltip = hideTooltip;
window.toggleReplyForm = toggleReplyForm;

function showShapeTooltip(event, shape) {
  if (!shape || shape === 'null' || shape === 'None') {
    shape = '정보 없음';
  }
  const shapeTips = {
    'Stratocaster': {
      desc: 'Fender의 대표적인 일렉기타 쉐입. 인체공학적 바디와 밝은 사운드가 특징.',
      img: '/static/uploads/shape_Stratocaster.png',
      label: '&lt;Fender Stratocaster&gt;'
    },
    'Les Paul': {
      desc: 'Gibson의 대표 쉐입. 두꺼운 바디와 깊고 두터운 사운드가 특징.',
      img: '/static/uploads/shape_lespaul.png',
      label: '&lt;Gibson Les Paul Standard&gt;'
    },
    'SG': {
      desc: 'Gibson의 얇고 가벼운 바디, 강렬한 록 사운드가 특징.',
      img: '/static/uploads/shape_sg.png',
      label: '&lt;Gibson SG Standard&gt;'
    },
    'Telecaster': {
      desc: 'Fender의 빈티지한 싱글컷 바디, 밝고 명료한 사운드가 특징.',
      img: '/static/uploads/shape_telecaster.png',
      label: '&lt;Fender Telecaster&gt;'
    },
    'Offset': {
      desc: '비대칭 바디. 인디/얼터너티브에 인기.',
      img: '/static/uploads/shape_offset.png',
      label: '&lt;Fender Jazzmaster&gt;'
    },
    'SuperStrat': {
      desc: '메탈/락 특화, 스트랫에 기반한 하이게인 픽업과 현대적 기능을 두루 갖춘 쉐입.',
      img: '/static/uploads/shape_superstrat.png',
      label: '&lt;Ibanez GIO Series&gt;'
    },
    'Semi-Hollow': {
      desc: '중앙은 솔리드, 바깥쪽은 비어있는 바디. 따뜻하고 풍부한 울림. 재즈/블루스에 적합.',
      img: '/static/uploads/shape_semihollow.png',
      label: '&lt;Gibson ES-335&gt;'
    },
    'Hollow': {
      desc: '완전히 빈 바디, 어쿠스틱에 가까운 울림. 재즈/클래식에 적합.',
      img: '/static/uploads/shape_hollow.png',
      label: '&lt;Gretsch Hollowbody&gt;'
    }
  };
  const tip = shapeTips[shape] || {desc: '사용자 정의 쉐이프 또는 정보 없음', img: null, label: ''};
  tooltip = document.getElementById('infoTooltip');
  let html = `<strong>${shape}</strong><br>${tip.desc}`;
  if (tip.img) {
    html += `<div style='text-align:center; margin-top:8px;'>`;
    html += `<img src='${tip.img}' alt='${shape} 이미지' style='max-width:180px; border-radius:6px; box-shadow:0 2px 8px #ccc; display:block; margin:0 auto;'>`;
    if (tip.label) {
      html += `<div style='margin-top:4px; font-size:0.95em; color:#444; text-align:center;'>${tip.label}</div>`;
    }
    html += `</div>`;
  }
  tooltip.innerHTML = html;
  tooltip.style.display = 'block';
  tooltip.style.left = event.pageX + 10 + 'px';
  tooltip.style.top = event.pageY + 10 + 'px';
}
window.showShapeTooltip = showShapeTooltip;

function drawPriceChart(labels, prices) {
  const chartDiv = document.getElementById("price-history-chart");
  chartDiv.innerHTML = '<canvas id="priceChart" height="220"></canvas>';
  if (window.priceChartObj) window.priceChartObj.destroy();
  const ctx = document.getElementById('priceChart').getContext('2d');
  window.priceChartObj = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: '거래가(만원)',
        data: prices,
        borderColor: '#0d6efd',
        backgroundColor: 'rgba(13,110,253,0.1)',
        tension: 0.2,
        pointRadius: 4,
        pointBackgroundColor: '#0d6efd',
        fill: true
      }]
    },
    options: {
      responsive: true,
      animation: {
        duration: 1500,
        easing: 'easeInOutQuart',
        onComplete: () => {
          // 애니메이션 완료 후 추가 동작 가능
        }
      },
      animations: {
        tension: {
          duration: 1500,
          easing: 'easeInOutQuart',
          from: 0.3,
          to: 0.2,
          loop: false
        },
        y: {
          duration: 1500,
          from: (ctx) => {
            if (ctx.type === 'data') {
              const chart = ctx.chart;
              const yScale = chart.scales.y;
              return yScale.getPixelForValue(0);
            }
          }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: { enabled: true }
      },
      scales: {
        x: { title: { display: true, text: '거래일' } },
        y: { title: { display: true, text: '만원' }, beginAtZero: true }
      }
    }
  });
}
