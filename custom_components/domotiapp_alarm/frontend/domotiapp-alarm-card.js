var nt=Object.defineProperty;var ot=(s,e,t)=>e in s?nt(s,e,{enumerable:!0,configurable:!0,writable:!0,value:t}):s[e]=t;var v=(s,e,t)=>ot(s,typeof e!="symbol"?e+"":e,t);var W=globalThis,G=W.ShadowRoot&&(W.ShadyCSS===void 0||W.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,X=Symbol(),_e=new WeakMap,V=class{constructor(e,t,i){if(this._$cssResult$=!0,i!==X)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o,t=this.t;if(G&&e===void 0){let i=t!==void 0&&t.length===1;i&&(e=_e.get(t)),e===void 0&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),i&&_e.set(t,e))}return e}toString(){return this.cssText}},z=s=>new V(typeof s=="string"?s:s+"",void 0,X),C=(s,...e)=>{let t=s.length===1?s[0]:e.reduce((i,n,o)=>i+(r=>{if(r._$cssResult$===!0)return r.cssText;if(typeof r=="number")return r;throw Error("Value passed to 'css' function must be a 'css' function result: "+r+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(n)+s[o+1],s[0]);return new V(t,s,X)},ge=(s,e)=>{if(G)s.adoptedStyleSheets=e.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(let t of e){let i=document.createElement("style"),n=W.litNonce;n!==void 0&&i.setAttribute("nonce",n),i.textContent=t.cssText,s.appendChild(i)}},Q=G?s=>s:s=>s instanceof CSSStyleSheet?(e=>{let t="";for(let i of e.cssRules)t+=i.cssText;return z(t)})(s):s;var{is:rt,defineProperty:at,getOwnPropertyDescriptor:lt,getOwnPropertyNames:dt,getOwnPropertySymbols:pt,getPrototypeOf:ht}=Object,B=globalThis,be=B.trustedTypes,ct=be?be.emptyScript:"",ut=B.reactiveElementPolyfillSupport,O=(s,e)=>s,ee={toAttribute(s,e){switch(e){case Boolean:s=s?ct:null;break;case Object:case Array:s=s==null?s:JSON.stringify(s)}return s},fromAttribute(s,e){let t=s;switch(e){case Boolean:t=s!==null;break;case Number:t=s===null?null:Number(s);break;case Object:case Array:try{t=JSON.parse(s)}catch{t=null}}return t}},$e=(s,e)=>!rt(s,e),ve={attribute:!0,type:String,converter:ee,reflect:!1,useDefault:!1,hasChanged:$e};Symbol.metadata??=Symbol("metadata"),B.litPropertyMetadata??=new WeakMap;var $=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??=[]).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=ve){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){let i=Symbol(),n=this.getPropertyDescriptor(e,i,t);n!==void 0&&at(this.prototype,e,n)}}static getPropertyDescriptor(e,t,i){let{get:n,set:o}=lt(this.prototype,e)??{get(){return this[t]},set(r){this[t]=r}};return{get:n,set(r){let h=n?.call(this);o?.call(this,r),this.requestUpdate(e,h,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??ve}static _$Ei(){if(this.hasOwnProperty(O("elementProperties")))return;let e=ht(this);e.finalize(),e.l!==void 0&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(O("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(O("properties"))){let t=this.properties,i=[...dt(t),...pt(t)];for(let n of i)this.createProperty(n,t[n])}let e=this[Symbol.metadata];if(e!==null){let t=litPropertyMetadata.get(e);if(t!==void 0)for(let[i,n]of t)this.elementProperties.set(i,n)}this._$Eh=new Map;for(let[t,i]of this.elementProperties){let n=this._$Eu(t,i);n!==void 0&&this._$Eh.set(n,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){let t=[];if(Array.isArray(e)){let i=new Set(e.flat(1/0).reverse());for(let n of i)t.unshift(Q(n))}else e!==void 0&&t.push(Q(e));return t}static _$Eu(e,t){let i=t.attribute;return i===!1?void 0:typeof i=="string"?i:typeof e=="string"?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(e=>this.enableUpdating=e),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(e=>e(this))}addController(e){(this._$EO??=new Set).add(e),this.renderRoot!==void 0&&this.isConnected&&e.hostConnected?.()}removeController(e){this._$EO?.delete(e)}_$E_(){let e=new Map,t=this.constructor.elementProperties;for(let i of t.keys())this.hasOwnProperty(i)&&(e.set(i,this[i]),delete this[i]);e.size>0&&(this._$Ep=e)}createRenderRoot(){let e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return ge(e,this.constructor.elementStyles),e}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(e=>e.hostConnected?.())}enableUpdating(e){}disconnectedCallback(){this._$EO?.forEach(e=>e.hostDisconnected?.())}attributeChangedCallback(e,t,i){this._$AK(e,i)}_$ET(e,t){let i=this.constructor.elementProperties.get(e),n=this.constructor._$Eu(e,i);if(n!==void 0&&i.reflect===!0){let o=(i.converter?.toAttribute!==void 0?i.converter:ee).toAttribute(t,i.type);this._$Em=e,o==null?this.removeAttribute(n):this.setAttribute(n,o),this._$Em=null}}_$AK(e,t){let i=this.constructor,n=i._$Eh.get(e);if(n!==void 0&&this._$Em!==n){let o=i.getPropertyOptions(n),r=typeof o.converter=="function"?{fromAttribute:o.converter}:o.converter?.fromAttribute!==void 0?o.converter:ee;this._$Em=n;let h=r.fromAttribute(t,o.type);this[n]=h??this._$Ej?.get(n)??h,this._$Em=null}}requestUpdate(e,t,i,n=!1,o){if(e!==void 0){let r=this.constructor;if(n===!1&&(o=this[e]),i??=r.getPropertyOptions(e),!((i.hasChanged??$e)(o,t)||i.useDefault&&i.reflect&&o===this._$Ej?.get(e)&&!this.hasAttribute(r._$Eu(e,i))))return;this.C(e,t,i)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(e,t,{useDefault:i,reflect:n,wrapped:o},r){i&&!(this._$Ej??=new Map).has(e)&&(this._$Ej.set(e,r??t??this[e]),o!==!0||r!==void 0)||(this._$AL.has(e)||(this.hasUpdated||i||(t=void 0),this._$AL.set(e,t)),n===!0&&this._$Em!==e&&(this._$Eq??=new Set).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}let e=this.scheduleUpdate();return e!=null&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[n,o]of this._$Ep)this[n]=o;this._$Ep=void 0}let i=this.constructor.elementProperties;if(i.size>0)for(let[n,o]of i){let{wrapped:r}=o,h=this[n];r!==!0||this._$AL.has(n)||h===void 0||this.C(n,void 0,o,h)}}let e=!1,t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),this._$EO?.forEach(i=>i.hostUpdate?.()),this.update(t)):this._$EM()}catch(i){throw e=!1,this._$EM(),i}e&&this._$AE(t)}willUpdate(e){}_$AE(e){this._$EO?.forEach(t=>t.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&=this._$Eq.forEach(t=>this._$ET(t,this[t])),this._$EM()}updated(e){}firstUpdated(e){}};$.elementStyles=[],$.shadowRootOptions={mode:"open"},$[O("elementProperties")]=new Map,$[O("finalized")]=new Map,ut?.({ReactiveElement:$}),(B.reactiveElementVersions??=[]).push("2.1.2");var ae=globalThis,xe=s=>s,Z=ae.trustedTypes,ye=Z?Z.createPolicy("lit-html",{createHTML:s=>s}):void 0,ze="$lit$",y=`lit$${Math.random().toFixed(9).slice(2)}$`,Ce="?"+y,mt=`<${Ce}>`,E=document,R=()=>E.createComment(""),H=s=>s===null||typeof s!="object"&&typeof s!="function",le=Array.isArray,ft=s=>le(s)||typeof s?.[Symbol.iterator]=="function",te=`[ 	
\f\r]`,P=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,ke=/-->/g,Ae=/>/g,k=RegExp(`>|${te}(?:([^\\s"'>=/]+)(${te}*=${te}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),Ee=/'/g,we=/"/g,je=/^(?:script|style|textarea|title)$/i,de=s=>(e,...t)=>({_$litType$:s,strings:e,values:t}),p=de(1),Jt=de(2),Xt=de(3),w=Symbol.for("lit-noChange"),d=Symbol.for("lit-nothing"),Se=new WeakMap,A=E.createTreeWalker(E,129);function Me(s,e){if(!le(s)||!s.hasOwnProperty("raw"))throw Error("invalid template strings array");return ye!==void 0?ye.createHTML(e):e}var _t=(s,e)=>{let t=s.length-1,i=[],n,o=e===2?"<svg>":e===3?"<math>":"",r=P;for(let h=0;h<t;h++){let l=s[h],a,u,c=-1,m=0;for(;m<l.length&&(r.lastIndex=m,u=r.exec(l),u!==null);)m=r.lastIndex,r===P?u[1]==="!--"?r=ke:u[1]!==void 0?r=Ae:u[2]!==void 0?(je.test(u[2])&&(n=RegExp("</"+u[2],"g")),r=k):u[3]!==void 0&&(r=k):r===k?u[0]===">"?(r=n??P,c=-1):u[1]===void 0?c=-2:(c=r.lastIndex-u[2].length,a=u[1],r=u[3]===void 0?k:u[3]==='"'?we:Ee):r===we||r===Ee?r=k:r===ke||r===Ae?r=P:(r=k,n=void 0);let _=r===k&&s[h+1].startsWith("/>")?" ":"";o+=r===P?l+mt:c>=0?(i.push(a),l.slice(0,c)+ze+l.slice(c)+y+_):l+y+(c===-2?h:_)}return[Me(s,o+(s[t]||"<?>")+(e===2?"</svg>":e===3?"</math>":"")),i]},D=class s{constructor({strings:e,_$litType$:t},i){let n;this.parts=[];let o=0,r=0,h=e.length-1,l=this.parts,[a,u]=_t(e,t);if(this.el=s.createElement(a,i),A.currentNode=this.el.content,t===2||t===3){let c=this.el.content.firstChild;c.replaceWith(...c.childNodes)}for(;(n=A.nextNode())!==null&&l.length<h;){if(n.nodeType===1){if(n.hasAttributes())for(let c of n.getAttributeNames())if(c.endsWith(ze)){let m=u[r++],_=n.getAttribute(c).split(y),S=/([.?@])?(.*)/.exec(m);l.push({type:1,index:o,name:S[2],strings:_,ctor:S[1]==="."?ie:S[1]==="?"?ne:S[1]==="@"?oe:M}),n.removeAttribute(c)}else c.startsWith(y)&&(l.push({type:6,index:o}),n.removeAttribute(c));if(je.test(n.tagName)){let c=n.textContent.split(y),m=c.length-1;if(m>0){n.textContent=Z?Z.emptyScript:"";for(let _=0;_<m;_++)n.append(c[_],R()),A.nextNode(),l.push({type:2,index:++o});n.append(c[m],R())}}}else if(n.nodeType===8)if(n.data===Ce)l.push({type:2,index:o});else{let c=-1;for(;(c=n.data.indexOf(y,c+1))!==-1;)l.push({type:7,index:o}),c+=y.length-1}o++}}static createElement(e,t){let i=E.createElement("template");return i.innerHTML=e,i}};function j(s,e,t=s,i){if(e===w)return e;let n=i!==void 0?t._$Co?.[i]:t._$Cl,o=H(e)?void 0:e._$litDirective$;return n?.constructor!==o&&(n?._$AO?.(!1),o===void 0?n=void 0:(n=new o(s),n._$AT(s,t,i)),i!==void 0?(t._$Co??=[])[i]=n:t._$Cl=n),n!==void 0&&(e=j(s,n._$AS(s,e.values),n,i)),e}var se=class{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){let{el:{content:t},parts:i}=this._$AD,n=(e?.creationScope??E).importNode(t,!0);A.currentNode=n;let o=A.nextNode(),r=0,h=0,l=i[0];for(;l!==void 0;){if(r===l.index){let a;l.type===2?a=new L(o,o.nextSibling,this,e):l.type===1?a=new l.ctor(o,l.name,l.strings,this,e):l.type===6&&(a=new re(o,this,e)),this._$AV.push(a),l=i[++h]}r!==l?.index&&(o=A.nextNode(),r++)}return A.currentNode=E,n}p(e){let t=0;for(let i of this._$AV)i!==void 0&&(i.strings!==void 0?(i._$AI(e,i,t),t+=i.strings.length-2):i._$AI(e[t])),t++}},L=class s{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(e,t,i,n){this.type=2,this._$AH=d,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=i,this.options=n,this._$Cv=n?.isConnected??!0}get parentNode(){let e=this._$AA.parentNode,t=this._$AM;return t!==void 0&&e?.nodeType===11&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=j(this,e,t),H(e)?e===d||e==null||e===""?(this._$AH!==d&&this._$AR(),this._$AH=d):e!==this._$AH&&e!==w&&this._(e):e._$litType$!==void 0?this.$(e):e.nodeType!==void 0?this.T(e):ft(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==d&&H(this._$AH)?this._$AA.nextSibling.data=e:this.T(E.createTextNode(e)),this._$AH=e}$(e){let{values:t,_$litType$:i}=e,n=typeof i=="number"?this._$AC(e):(i.el===void 0&&(i.el=D.createElement(Me(i.h,i.h[0]),this.options)),i);if(this._$AH?._$AD===n)this._$AH.p(t);else{let o=new se(n,this),r=o.u(this.options);o.p(t),this.T(r),this._$AH=o}}_$AC(e){let t=Se.get(e.strings);return t===void 0&&Se.set(e.strings,t=new D(e)),t}k(e){le(this._$AH)||(this._$AH=[],this._$AR());let t=this._$AH,i,n=0;for(let o of e)n===t.length?t.push(i=new s(this.O(R()),this.O(R()),this,this.options)):i=t[n],i._$AI(o),n++;n<t.length&&(this._$AR(i&&i._$AB.nextSibling,n),t.length=n)}_$AR(e=this._$AA.nextSibling,t){for(this._$AP?.(!1,!0,t);e!==this._$AB;){let i=xe(e).nextSibling;xe(e).remove(),e=i}}setConnected(e){this._$AM===void 0&&(this._$Cv=e,this._$AP?.(e))}},M=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,i,n,o){this.type=1,this._$AH=d,this._$AN=void 0,this.element=e,this.name=t,this._$AM=n,this.options=o,i.length>2||i[0]!==""||i[1]!==""?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=d}_$AI(e,t=this,i,n){let o=this.strings,r=!1;if(o===void 0)e=j(this,e,t,0),r=!H(e)||e!==this._$AH&&e!==w,r&&(this._$AH=e);else{let h=e,l,a;for(e=o[0],l=0;l<o.length-1;l++)a=j(this,h[i+l],t,l),a===w&&(a=this._$AH[l]),r||=!H(a)||a!==this._$AH[l],a===d?e=d:e!==d&&(e+=(a??"")+o[l+1]),this._$AH[l]=a}r&&!n&&this.j(e)}j(e){e===d?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}},ie=class extends M{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===d?void 0:e}},ne=class extends M{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==d)}},oe=class extends M{constructor(e,t,i,n,o){super(e,t,i,n,o),this.type=5}_$AI(e,t=this){if((e=j(this,e,t,0)??d)===w)return;let i=this._$AH,n=e===d&&i!==d||e.capture!==i.capture||e.once!==i.once||e.passive!==i.passive,o=e!==d&&(i===d||n);n&&this.element.removeEventListener(this.name,this,i),o&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,e):this._$AH.handleEvent(e)}},re=class{constructor(e,t,i){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(e){j(this,e)}};var gt=ae.litHtmlPolyfillSupport;gt?.(D,L),(ae.litHtmlVersions??=[]).push("3.3.3");var Te=(s,e,t)=>{let i=t?.renderBefore??e,n=i._$litPart$;if(n===void 0){let o=t?.renderBefore??null;i._$litPart$=n=new L(e.insertBefore(R(),o),o,void 0,t??{})}return n._$AI(s),n};var pe=globalThis,g=class extends ${constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let e=super.createRenderRoot();return this.renderOptions.renderBefore??=e.firstChild,e}update(e){let t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=Te(t,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return w}};g._$litElement$=!0,g.finalized=!0,pe.litElementHydrateSupport?.({LitElement:g});var bt=pe.litElementPolyfillSupport;bt?.({LitElement:g});(pe.litElementVersions??=[]).push("4.2.2");var x="domotiapp-alarm-card",he="domotiapp-alarm-card-editor",Ne="domotiapp-alarm-editor",Ve="DomotiApp Alarm",Oe="https://github.com/Sven2410/domotiapp-alarm",b="domotiapp_alarm",f=Object.freeze({get:`${b}/alarms/get`,save:`${b}/alarms/save`,setEnabled:`${b}/alarms/set_enabled`,skipNext:`${b}/alarms/skip_next`,delete:`${b}/alarms/delete`,stop:`${b}/alarms/stop`,clearMessage:`${b}/alarms/clear_message`,search:`${b}/sound/search`,entities:`${b}/entities/list`,previewStart:`${b}/preview/start`,subscribe:`${b}/updates/subscribe`}),F="#026FA1";var vt="07:00";var $t=["uri","name","media_type","image"],xt="Let op: deze tijd bestaat twee nachten per jaar niet, of twee keer. Bij de overgang naar zomertijd wordt het uur van 02:00 tot 03:00 overgeslagen; die nacht gaat deze wekker niet af. Bij de overgang naar wintertijd komt dat uur twee keer voorbij; die nacht gaat hij twee keer af. Kies een tijd v\xF3\xF3r 02:00 of n\xE1 03:00 als dat een probleem is.",yt="Dit geluid stopt van zichzelf. Een los nummer is na een paar minuten voorbij; daarna is het stil. Kies een afspeellijst of een radiostation als de wekker moet blijven spelen tot je hem uitzet.";var kt="Music Assistant Wekker",At="Verlichting Wekker";function q(){return{id:null,name:"",time:vt,days:[],enabled:!0,sound:null,endless:null,speaker:"",volume_pct:40,light:null}}function Pe(s){let e=q();return!s||typeof s!="object"?e:{id:typeof s.id=="string"?s.id:null,name:typeof s.name=="string"?s.name:"",time:ce(s.time)?s.time:e.time,days:Array.isArray(s.days)?[...s.days]:[],enabled:s.enabled!==!1,sound:U(s.sound),endless:null,speaker:typeof s.speaker=="string"?s.speaker:"",volume_pct:Number.isInteger(s.volume_pct)?s.volume_pct:e.volume_pct,light:s.light&&typeof s.light=="object"?{entity_id:s.light.entity_id,brightness_pct:Number.isInteger(s.light.brightness_pct)?s.light.brightness_pct:60}:null}}function U(s){if(!s||typeof s!="object"||Array.isArray(s)||typeof s.uri!="string"||!s.uri)return null;let e={};for(let t of $t)e[t]=s[t]===void 0?null:s[t];return e}function ce(s){if(typeof s!="string"||s.length!==5||s[2]!==":")return!1;let e=Number(s.slice(0,2)),t=Number(s.slice(3));return!/^\d\d$/.test(s.slice(0,2))||!/^\d\d$/.test(s.slice(3))?!1:e>=0&&e<=23&&t>=0&&t<=59}function ue(s){let e=[];return!s||typeof s!="object"?{ok:!1,ontbreekt:["alles"]}:((typeof s.name!="string"||!s.name.trim())&&e.push("een naam"),ce(s.time)||e.push("een geldige tijd"),s.speaker||e.push("een speaker"),(!s.sound||!s.sound.uri)&&e.push("een geluid"),(!Number.isInteger(s.volume_pct)||s.volume_pct<1||s.volume_pct>100)&&e.push("een volume tussen 1 en 100"),{ok:e.length===0,ontbreekt:e})}function Re(s){let e={name:(s.name||"").trim(),time:s.time,days:[...new Set(s.days||[])].sort((t,i)=>t-i),enabled:s.enabled!==!1,sound:U(s.sound),speaker:s.speaker,volume_pct:s.volume_pct,light:s.light?{entity_id:s.light.entity_id,brightness_pct:s.light.brightness_pct}:null};return s.id&&(e.id=s.id),e}function He(s,e){let t=new Set(s||[]);return t.has(e)?t.delete(e):t.add(e),[...t].sort((i,n)=>i-n)}function De(s){return ce(s)&&s.slice(0,2)==="02"?xt:null}function Le(s){return s===!1?yt:null}function Ue(s){return typeof s?.endless=="boolean"?s.endless:null}function Y(s,e){let t=e==="lamp",i=t?At:kt,n=t?"lampen":"speakers";return!s||typeof s!="object"?`De lijst met ${n} is niet op te halen.`:s.label_exists===!1?`Het label '${i}' bestaat nog niet. De beheerder moet dat label aanmaken en op de ${n} zetten die als wekker mogen dienen.`:Array.isArray(s.entities)&&s.entities.length>0?null:Number(s.filtered_out)>0?t?`De entiteiten met het label '${i}' zijn geen lampen.`:"De gelabelde speakers zijn geen Music Assistant-speakers, of ze kunnen geen volume instellen.":`Er zijn nog geen ${n} met het label '${i}'.`}function Ie(s,e){return Y(e,"speaker")!==null?!1:ue(s).ok}var wt=[[1,"ma"],[2,"di"],[3,"wo"],[4,"do"],[5,"vr"],[6,"za"],[7,"zo"]],St=[["","Alles"],["playlist","Afspeellijsten"],["radio","Radio"],["artist","Artiesten"],["album","Albums"],["track","Nummers"],["podcast","Podcasts"]],I="M13,9H11V7H13M13,17H11V11H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z",zt="M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z",Ct="M6,2H18V8H18V8L14,12L18,16V16H18V22H6V16H6V16L10,12L6,8V8H6V2M16,16.5L12,12.5L8,16.5V20H16V16.5M12,11.5L16,7.5V4H8V7.5L12,11.5Z",T=class extends g{constructor(){super(),this._concept=q(),this._zoekterm="",this._soort="",this._treffers=null,this._zoekt=!1,this._melding=null,this._speelt=!1,this._bezig=!1,this._afmeldenVoorbeeld=null,this._opEscape=e=>{e.key==="Escape"&&this._annuleren()}}connectedCallback(){super.connectedCallback(),window.addEventListener("keydown",this._opEscape,!0)}disconnectedCallback(){super.disconnectedCallback(),window.removeEventListener("keydown",this._opEscape,!0),this._stopVoorbeeld()}willUpdate(e){e.has("wekker")&&(this._concept=this.wekker?Pe(this.wekker):q(),this._treffers=null,this._zoekterm="",this._melding=null)}_zet(e){this._concept={...this._concept,...e}}async _startVoorbeeld(){if(!(this._speelt||!this.hass)){if(!this._concept.speaker||!this._concept.sound){this._melding={tekst:"Kies eerst een speaker en een geluid.",fout:!0};return}this._melding=null;try{this._afmeldenVoorbeeld=await this.hass.connection.subscribeMessage(()=>{},{type:f.previewStart,speaker:this._concept.speaker,sound:U(this._concept.sound),volume_pct:this._concept.volume_pct}),this._speelt=!0}catch(e){this._melding={tekst:e?.message??"Het voorbeeld kon niet starten.",fout:!0}}}}_stopVoorbeeld(){if(this._afmeldenVoorbeeld){try{this._afmeldenVoorbeeld()}catch(e){console.warn(`domotiapp-alarm-editor: afmelden mislukt: ${e?.message??e}`)}this._afmeldenVoorbeeld=null}this._speelt=!1}async _zoek(){let e=(this._zoekterm||"").trim();if(!(!e||!this.hass)){this._zoekt=!0,this._melding=null;try{let t={type:f.search,query:e,limit:20};this._soort&&(t.media_types=[this._soort]);let i=await this.hass.callWS(t);this._treffers=i.results??[]}catch(t){this._treffers=[],this._melding={tekst:t?.message??"Zoeken is mislukt.",fout:!0}}finally{this._zoekt=!1}}}_kiesGeluid(e){this._zet({sound:U(e),endless:Ue(e)}),this._treffers=null}async _opslaan(){if(this._bezig||!this.hass)return;let e=ue(this._concept);if(!e.ok){this._melding={tekst:`Er ontbreekt nog ${e.ontbreekt.join(", ")}.`,fout:!0};return}this._bezig=!0;try{let t=await this.hass.callWS({type:f.save,person:this.person,alarm:Re(this._concept)});this._stopVoorbeeld(),this.dispatchEvent(new CustomEvent("editor-opgeslagen",{detail:{toestand:t},bubbles:!0,composed:!0}))}catch(t){this._melding={tekst:t?.message??"Opslaan is mislukt.",fout:!0}}finally{this._bezig=!1}}_annuleren(){this._stopVoorbeeld(),this.dispatchEvent(new CustomEvent("editor-dicht",{bubbles:!0,composed:!0}))}_svg(e){return p`<svg class="icoon" viewBox="0 0 24 24" aria-hidden="true">
      <path d=${e} />
    </svg>`}render(){if(!this.hass)return d;let e=this._concept,t=this.entiteiten?.speakers,i=this.entiteiten?.lights,n=Y(t,"speaker"),o=Y(i,"lamp"),r=De(e.time),h=Le(e.endless),l=Ie(e,t);return p`
      <div class="kop">
        <h2>${e.id?"Wekker bewerken":"Nieuwe wekker"}</h2>
      </div>

      <div class="blok">
        <label class="veld" for="tijd">Tijd</label>
        <input
          id="tijd"
          type="time"
          .value=${e.time}
          required
          @input=${a=>this._zet({time:a.target.value})}
        />
        ${r?p`<div class="waarschuwing">
              ${this._svg(I)}<span>${r}</span>
            </div>`:d}
      </div>

      <div class="blok">
        <label class="veld">Herhaling</label>
        <div class="dagen">
          ${wt.map(([a,u])=>p`<button
              type="button"
              aria-pressed=${e.days.includes(a)?"true":"false"}
              aria-label=${u}
              @click=${()=>this._zet({days:He(e.days,a)})}
            >
              ${u}
            </button>`)}
        </div>
        <div class="uitleg">
          ${e.days.length===0?"Geen dag aangevinkt: deze wekker gaat \xE9\xE9n keer af, de eerstvolgende keer dat die tijd voorbijkomt.":"Deze wekker herhaalt zich op de aangevinkte dagen."}
        </div>
      </div>

      <div class="blok">
        <label class="veld" for="naam">Naam</label>
        <input
          id="naam"
          type="text"
          .value=${e.name}
          placeholder="Bijvoorbeeld: Werk"
          @input=${a=>this._zet({name:a.target.value})}
        />
      </div>

      <div class="blok">
        <label class="veld" for="speaker">Speaker</label>
        ${n?p`<div class="uitleg">${this._svg(I)}<span>${n}</span></div>`:p`<select
              id="speaker"
              .value=${e.speaker}
              @change=${a=>this._zet({speaker:a.target.value})}
            >
              <option value="">Kies een speaker…</option>
              ${(t?.entities??[]).map(a=>p`<option value=${a.entity_id} ?selected=${a.entity_id===e.speaker}>
                  ${a.name}
                </option>`)}
            </select>`}
      </div>

      <div class="blok">
        <label class="veld" for="zoek">Geluid</label>
        ${e.sound?p`<div class="gekozen">
              ${e.sound.image?p`<img src=${e.sound.image} alt="" />`:d}
              <span>${e.sound.name||e.sound.uri}</span>
              <span class="soort" style="margin-left:auto">${e.sound.media_type??""}</span>
            </div>`:d}
        <div class="rij" style="margin-top:8px">
          <input
            id="zoek"
            type="text"
            .value=${this._zoekterm}
            placeholder="Zoek media"
            @input=${a=>{this._zoekterm=a.target.value}}
            @keydown=${a=>{a.key==="Enter"&&(a.preventDefault(),this._zoek())}}
          />
          <select
            aria-label="Soort"
            @change=${a=>{this._soort=a.target.value}}
            style="width:auto"
          >
            ${St.map(([a,u])=>p`<option value=${a}>${u}</option>`)}
          </select>
          <button
            class="knop zoekknop"
            type="button"
            title="Zoeken"
            aria-label="Zoeken"
            ?disabled=${this._zoekt}
            @click=${()=>this._zoek()}
          >
            ${this._svg(this._zoekt?Ct:zt)}
          </button>
        </div>
        ${this._treffers?p`<div class="treffers">
              ${this._treffers.length===0?p`<div class="treffer">Niets gevonden.</div>`:this._treffers.map(a=>p`<button
                      class="treffer"
                      type="button"
                      @click=${()=>this._kiesGeluid(a)}
                    >
                      ${a.image?p`<img src=${a.image} alt="" />`:d}
                      <span>${a.name}</span>
                      <span class="soort">${a.media_type??""}</span>
                    </button>`)}
            </div>`:d}
        ${h?p`<div class="waarschuwing">${this._svg(I)}<span>${h}</span></div>`:d}
      </div>

      <div class="blok">
        <label class="veld" for="volume">Volume: ${e.volume_pct}%</label>
        <input
          id="volume"
          type="range"
          min="1"
          max="100"
          .value=${String(e.volume_pct)}
          @input=${a=>this._zet({volume_pct:Number(a.target.value)})}
        />
        <div class="uitleg">
          Het niveau waar de wekker in twintig seconden naartoe groeit.
        </div>
      </div>

      <div class="blok">
        <label class="veld" for="lamp">Wake-up light (optioneel)</label>
        ${o?p`<div class="uitleg">${this._svg(I)}<span>${o}</span></div>`:p`
              <select
                id="lamp"
                @change=${a=>this._zet({light:a.target.value?{entity_id:a.target.value,brightness_pct:e.light?.brightness_pct??60}:null})}
              >
                <option value="">Geen lamp</option>
                ${(i?.entities??[]).map(a=>p`<option
                    value=${a.entity_id}
                    ?selected=${a.entity_id===e.light?.entity_id}
                  >
                    ${a.name}
                  </option>`)}
              </select>
              ${e.light?p`<label class="veld" style="margin-top:10px" for="helderheid">
                      Helderheid: ${e.light.brightness_pct}%
                    </label>
                    <input
                      id="helderheid"
                      type="range"
                      min="1"
                      max="100"
                      .value=${String(e.light.brightness_pct)}
                      @input=${a=>this._zet({light:{...e.light,brightness_pct:Number(a.target.value)}})}
                    />`:d}
            `}
      </div>

      ${this._melding?p`<div class="blok">
            <div class="waarschuwing ${this._melding.fout?"fout":""}">
              ${this._svg(I)}<span>${this._melding.tekst}</span>
            </div>
          </div>`:d}

      <div class="voet">
        <button
          class="knop voorbeeld"
          type="button"
          @click=${()=>this._speelt?this._stopVoorbeeld():this._startVoorbeeld()}
        >
          ${this._speelt?"Voorbeeld stoppen":"Voorbeeld"}
        </button>
        <button class="knop" type="button" @click=${()=>this._annuleren()}>Annuleren</button>
        <button
          class="knop primair"
          type="button"
          ?disabled=${!l||this._bezig}
          @click=${()=>this._opslaan()}
        >
          Opslaan
        </button>
      </div>
    `}};v(T,"properties",{hass:{attribute:!1},person:{attribute:!1},wekker:{attribute:!1},entiteiten:{attribute:!1},_concept:{state:!0},_zoekterm:{state:!0},_soort:{state:!0},_treffers:{state:!0},_zoekt:{state:!0},_melding:{state:!0},_speelt:{state:!0},_bezig:{state:!0}}),v(T,"styles",C`
    :host {
      --domotiapp-accent: ${z(F)};
      display: block;
    }
    .blok {
      padding: 12px 16px;
      border-bottom: 1px solid var(--divider-color);
    }
    .kop {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      border-bottom: 1px solid var(--divider-color);
    }
    .kop h2 {
      margin: 0;
      flex: 1;
      font-size: var(--ha-font-size-l, 16px);
      font-weight: 500;
      color: var(--primary-text-color);
    }
    label.veld {
      display: block;
      color: var(--secondary-text-color);
      font-size: var(--ha-font-size-s, 12px);
      margin-bottom: 6px;
    }
    input[type="text"],
    input[type="time"],
    select {
      width: 100%;
      box-sizing: border-box;
      padding: 10px;
      border: 1px solid var(--divider-color);
      border-radius: 6px;
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color);
      font-family: inherit;
      font-size: var(--ha-font-size-m, 14px);
    }
    input[type="time"] {
      font-size: 24px;
      font-variant-numeric: tabular-nums;
    }
    input[type="range"] {
      width: 100%;
      accent-color: var(--domotiapp-accent);
    }
    .dagen {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }
    .dagen button {
      flex: 1 1 0;
      min-width: 38px;
      padding: 8px 0;
      border: 1px solid var(--divider-color);
      border-radius: 18px;
      background: none;
      color: var(--secondary-text-color);
      cursor: pointer;
      font-family: inherit;
      font-size: var(--ha-font-size-s, 12px);
    }
    .dagen button[aria-pressed="true"] {
      background: var(--domotiapp-accent);
      border-color: var(--domotiapp-accent);
      color: #fff;
    }
    .rij {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .rij > :first-child {
      flex: 1;
    }
    button.knop {
      border: 1px solid var(--divider-color);
      border-radius: 18px;
      background: none;
      color: var(--primary-text-color);
      padding: 9px 16px;
      cursor: pointer;
      font-family: inherit;
      font-size: var(--ha-font-size-m, 14px);
      white-space: nowrap;
    }
    button.knop:hover:not(:disabled) {
      background: var(--divider-color);
    }
    button.knop:disabled {
      opacity: 0.45;
      cursor: not-allowed;
    }
    /* Het vergrootglas naast het zoekveld: vierkant en zo smal mogelijk, want op
       een telefoon vecht deze regel om de breedte met het veld ernaast. */
    button.knop.zoekknop {
      flex: 0 0 auto;
      width: 42px;
      padding: 9px 0;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }
    button.knop.primair {
      background: var(--domotiapp-accent);
      border-color: var(--domotiapp-accent);
      color: #fff;
    }
    .waarschuwing,
    .uitleg {
      display: flex;
      gap: 8px;
      align-items: flex-start;
      color: var(--secondary-text-color);
      font-size: var(--ha-font-size-s, 12px);
      margin-top: 8px;
    }
    .waarschuwing.fout {
      color: var(--error-color);
    }
    .icoon {
      width: 18px;
      height: 18px;
      flex: 0 0 auto;
      fill: currentColor;
    }
    .treffers {
      margin-top: 8px;
      max-height: 260px;
      overflow-y: auto;
      border: 1px solid var(--divider-color);
      border-radius: 6px;
    }
    .treffer {
      display: flex;
      align-items: center;
      gap: 10px;
      width: 100%;
      padding: 8px 10px;
      border: none;
      border-bottom: 1px solid var(--divider-color);
      background: none;
      color: var(--primary-text-color);
      cursor: pointer;
      text-align: left;
      font-family: inherit;
      font-size: var(--ha-font-size-s, 12px);
    }
    .treffer:last-child {
      border-bottom: none;
    }
    .treffer:hover {
      background: var(--divider-color);
    }
    .treffer img,
    .gekozen img {
      width: 40px;
      height: 40px;
      border-radius: 4px;
      object-fit: cover;
      flex: 0 0 auto;
      background: var(--divider-color);
    }
    .treffer .soort {
      color: var(--secondary-text-color);
      margin-left: auto;
      white-space: nowrap;
    }
    .gekozen {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px;
      border: 1px solid var(--divider-color);
      border-radius: 6px;
      color: var(--primary-text-color);
      font-size: var(--ha-font-size-s, 12px);
    }
    .voet {
      display: flex;
      gap: 8px;
      justify-content: flex-end;
      padding: 12px 16px;
    }
    .voet .voorbeeld {
      margin-right: auto;
    }
  `);var Ke="person",jt="Kies een persoon in de kaartinstellingen.",We="De gekozen persoon bestaat niet meer.",Mt="De opgeslagen wekkers van deze persoon zijn onleesbaar.",bs=Object.freeze(["grid_options","layout_options","view_layout","visibility"]);function Ge(s){if(!s||typeof s!="object"||Array.isArray(s))throw new Error("De kaartconfig ontbreekt of is geen object.");let e=s.person;if(e==null||e==="")return{...s};if(typeof e!="string")throw new Error("'person' moet een entity-ID zijn, zoals person.sven.");if(!e.startsWith(`${Ke}.`))throw new Error(`'${e}' zit niet in het domein ${Ke}. Kies een persoon, zoals person.sven.`);return{...s}}function Be(s){return{type:`custom:${s}`}}function Ze(s,e){return s?e?{soort:"ok",tekst:null,isFout:!1}:{soort:"weg",tekst:We,isFout:!0}:{soort:"ontbreekt",tekst:jt,isFout:!1}}function Fe(s,e){return s==="not_found"?We:s==="home_assistant_error"?Mt:e||"Er ging iets mis bij het ophalen van de wekkers."}function Ye(s,e,t,i){let n=s.bottom+4,o=s.top-t.hoogte-4,r=n+t.hoogte<=e.bottom,h=o>=e.top,l,a;r?(l=n,a="onder"):h?(l=o,a="boven"):(l=n,a="onder");let u=r||h;return l=qe(l,4,i.hoogte-t.hoogte-4),{left:qe(s.right-t.breedte,4,i.breedte-t.breedte-4),top:l,richting:a,binnenKaart:u}}function qe(s,e,t){return Math.max(e,Math.min(s,t))}var Tt="home-assistant";function Je({leesRegistry:s,definities:e,waarschuw:t=()=>{},plan:i=(l,a)=>setTimeout(l,a),nu:n=()=>Date.now(),marker:o=Tt,intervalMs:r=20,maxWachtMs:h=1e4}){let l=n();function a(){let m=s();if(!m)return!1;for(let[_,S]of e)try{m.get(_)||m.define(_,S)}catch(fe){t(`kon ${_} niet registreren: ${fe&&fe.message}`)}return!0}function u(){let m=s();return!m||!m.get(o)?!1:a()}if(u())return!0;let c=()=>{if(!u()){if(n()-l>=h){t(`${o} is na ${h} ms niet verschenen; de kaart wordt alsnog geregistreerd`),a();return}i(c,r)}};return i(c,r),!1}var Nt=["ma","di","wo","do","vr","za","zo"],Vt="Geen wekkers ingesteld",Ot="Eenmalig",Pt="Eenmalig \u2014 afgelopen",Rt="Morgen overgeslagen",Ht="Geen wekker actief",Xe="Stoppen",Dt="Er is een melding over deze wekker, maar de tekst ontbreekt.";function Lt(s){return!Array.isArray(s)||s.length===0?Ot:[...new Set(s)].sort((t,i)=>t-i).map(t=>Nt[t-1]??"?").join(" ")}function Ut(s,e){return!s||Array.isArray(s.days)&&s.days.length>0?!1:Date.parse(s?.one_shot_at??"")<=e}function Qe(s,e){return Ut(s,e)?Pt:s?.skip_next?Rt:Lt(s?.days)}function et(s){let e=s?.last_message;return!e||typeof e!="object"||Array.isArray(e)?null:{tekst:typeof e.text=="string"&&e.text.trim()?e.text:Dt,severity:e.severity==="error"?"error":"notice",isFout:e.severity==="error",kind:typeof e.kind=="string"?e.kind:null}}function tt(s){let e=s?.alarms;if(!Array.isArray(e)||e.length===0)return Vt;let t=s?.next_fire?.text;return typeof t=="string"&&t.trim()?t:Ht}function st(s,e){let t=[...new Set((e??[]).filter(r=>typeof r=="string"))];if(t.length===0)return null;let i=t.map(r=>(s??[]).find(h=>h?.id===r)).filter(Boolean),n=i.map(r=>r.name).filter(Boolean),o=[...new Set(i.map(r=>r.time).filter(Boolean))];return{ids:t,naam:n.length?n.join(" en "):"Wekker",tijd:o.join(" en ")}}var It="1.0.1",Kt="M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z",Wt="M12,16A2,2 0 0,1 14,18A2,2 0 0,1 12,20A2,2 0 0,1 10,18A2,2 0 0,1 12,16M12,10A2,2 0 0,1 14,12A2,2 0 0,1 12,14A2,2 0 0,1 10,12A2,2 0 0,1 12,10M12,4A2,2 0 0,1 14,6A2,2 0 0,1 12,8A2,2 0 0,1 10,6A2,2 0 0,1 12,4Z",it="M13,9H11V7H13M13,17H11V11H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z",Gt="M13,14H11V9H13M13,18H11V16H13M1,21H23L12,2L1,21Z",J=(s,e="icoon")=>p`<svg class=${e} viewBox="0 0 24 24" aria-hidden="true">
    <path d=${s} />
  </svg>`,K=class extends g{constructor(){super(),this._toestand=null,this._fout=null,this._menuVoor=null,this._menuPositie=null,this._bevestigVoor=null,this._bezig=!1,this._tijdelijkeMelding=null,this._editorVoor=void 0,this._entiteiten=null,this._abonnementVoor=null,this._afmelden=null,this._menuAnker=null,this._opVerplaatsing=()=>this._sluitMenu()}setConfig(e){let t=Ge(e),i=t.person!==this._config?.person;this._config=t,i&&(this._toestand=null,this._fout=null,this._sluitMenu(),this._bevestigVoor=null,this._herstartAbonnement())}static getConfigElement(){return document.createElement(he)}static getStubConfig(){return Be(x)}getGridOptions(){return{rows:"auto",columns:12,min_columns:6}}getCardSize(){if(this._stop())return 3;let e=this._toestand?.alarms?.length??0;return 1+Math.max(e,1)}connectedCallback(){super.connectedCallback(),this._herstartAbonnement()}disconnectedCallback(){super.disconnectedCallback(),this._stopAbonnement(),this._sluitMenu()}updated(e){e.has("hass")&&this.hass&&this._startAbonnement(),this._plaatsMenu()}_wisselMenu(e,t){if(this._menuVoor===e.id){this._sluitMenu();return}let i=t.currentTarget.getBoundingClientRect();this._menuAnker={top:i.top,bottom:i.bottom,right:i.right},this._menuPositie=null,this._menuVoor=e.id,window.addEventListener("scroll",this._opVerplaatsing,!0),window.addEventListener("resize",this._opVerplaatsing)}_sluitMenu(){this._menuVoor=null,this._menuPositie=null,this._menuAnker=null,window.removeEventListener("scroll",this._opVerplaatsing,!0),window.removeEventListener("resize",this._opVerplaatsing)}_plaatsMenu(){if(!this._menuVoor||this._menuPositie||!this._menuAnker)return;let e=this.renderRoot?.querySelector(".menu"),t=this.renderRoot?.querySelector("ha-card");if(!e||!t)return;let i=e.getBoundingClientRect(),n=t.getBoundingClientRect();this._menuPositie=Ye(this._menuAnker,{top:n.top,bottom:n.bottom},{breedte:i.width,hoogte:i.height},{breedte:window.innerWidth,hoogte:window.innerHeight})}async _startAbonnement(){let e=this._config?.person;if(!(!this.hass||!e||!this.isConnected)&&this._abonnementVoor!==e){this._abonnementVoor=e;try{let t=await this.hass.connection.subscribeMessage(i=>this._opGebeurtenis(i),{type:f.subscribe,person:e});if(this._abonnementVoor!==e){t();return}this._afmelden=t}catch(t){console.warn(`${x}: abonneren mislukt: ${t?.message??t}`)}await this._haalOp()}}_stopAbonnement(){if(this._afmelden){try{this._afmelden()}catch(e){console.warn(`${x}: afmelden mislukt: ${e?.message??e}`)}this._afmelden=null}this._abonnementVoor=null}_herstartAbonnement(){this._stopAbonnement(),this._startAbonnement()}_opGebeurtenis(e){let t=e?.alarm_id,i=e?.event;if(typeof t=="string"&&this._toestand){let n=new Set(this._toestand.ringing??[]);i==="started"?n.add(t):n.delete(t),this._toestand={...this._toestand,ringing:[...n]}}this._haalOp()}async _haalOp(){let e=this._config?.person;if(!(!this.hass||!e))try{let t=await this.hass.callWS({type:f.get,person:e});if(this._config?.person!==e)return;this._toestand=t,this._fout=null}catch(t){if(this._config?.person!==e)return;this._toestand=null,this._fout=Fe(t?.code,t?.message)}}async _roep(e){if(!(!this.hass||this._bezig)){this._bezig=!0;try{let t=await this.hass.callWS(e);t&&typeof t=="object"&&(this._toestand=t,this._fout=null)}catch(t){this._toon(t?.message??"De opdracht is niet gelukt.")}finally{this._bezig=!1}}}async _openEditor(e){if(this._sluitMenu(),this._bevestigVoor=null,this._editorVoor=e,!!this.hass)try{this._entiteiten=await this.hass.callWS({type:f.entities})}catch(t){this._entiteiten=null,console.warn(`${x}: entiteitenlijst ophalen mislukt: ${t?.message??t}`)}}_sluitEditor(){this._editorVoor=void 0}_toon(e){this._tijdelijkeMelding=e,clearTimeout(this._meldingTimer),this._meldingTimer=setTimeout(()=>{this._tijdelijkeMelding=null},6e3)}_person(){return this._config?.person}_zetAan(e,t){this._roep({type:f.setEnabled,person:this._person(),alarm_id:e.id,enabled:t})}_overslaan(e){this._sluitMenu(),this._roep({type:f.skipNext,person:this._person(),alarm_id:e.id,skip:!e.skip_next})}_verwijder(e){this._bevestigVoor=null,this._roep({type:f.delete,person:this._person(),alarm_id:e.id})}_begrepen(e){this._roep({type:f.clearMessage,person:this._person(),alarm_id:e.id})}async _stopAlles(e){for(let t of e)await this._roep({type:f.stop,person:this._person(),alarm_id:t})}_stop(){return this._toestand?st(this._toestand.alarms,this._toestand.ringing):null}render(){if(!this._config)return d;let e=this._config.person,t=!!(e&&this.hass?.states?.[e]),i=Ze(e,t);if(i.soort!=="ok")return this._mededeling(i.tekst,i.isFout);if(this._fout)return this._mededeling(this._fout,!0);if(!this._toestand)return this._mededeling("Wekkers ophalen\u2026",!1);let n=this._stop();return this._editorVoor!==void 0&&!n?p`<ha-card>
        <domotiapp-alarm-editor
          .hass=${this.hass}
          .person=${this._config.person}
          .wekker=${this._editorVoor}
          .entiteiten=${this._entiteiten}
          @editor-dicht=${()=>this._sluitEditor()}
          @editor-opgeslagen=${o=>{this._toestand=o.detail.toestand,this._sluitEditor()}}
        ></domotiapp-alarm-editor>
      </ha-card>`:p`<ha-card>
      ${this._menuVoor?p`<div class="sluiter" @click=${()=>this._sluitMenu()}></div>`:d}
      ${n?this._stopknop(n):this._lijst()}
      ${this._tijdelijkeMelding?p`<div class="onderrij">
            ${J(it,"icoon klein")}
            <span class="boodschap">${this._tijdelijkeMelding}</span>
          </div>`:d}
    </ha-card>`}_mededeling(e,t){return p`<ha-card>
      <div class="mededeling ${t?"fout":""}">${e}</div>
    </ha-card>`}_stopknop(e){return p`<button
      class="stopknop"
      @click=${()=>this._stopAlles(e.ids)}
    >
      <div class="stop-tijd">${e.tijd}</div>
      <div class="stop-naam">${e.naam}</div>
      <div class="stop-woord">${Xe}</div>
    </button>`}_lijst(){let e=this._toestand.alarms??[],t=Date.now();return p`
      <div class="kop ${e.length===0?"leeg":""}">
        <span class="volgende">${tt(this._toestand)}</span>
        <button
          class="icoonknop"
          title="Wekker toevoegen"
          aria-label="Wekker toevoegen"
          @click=${()=>this._openEditor(null)}
        >
          ${J(Kt)}
        </button>
      </div>
      ${e.map(i=>this._rij(i,t))}
    `}_rij(e,t){let i=et(e),n=!!e.enabled;return p`
      <div class="rij ${n?"":"uit"}">
        <button
          class="tikvlak"
          type="button"
          aria-label="Wekker ${e.name} bewerken"
          @click=${()=>this._openEditor(e)}
        >
          <div class="tijd">${e.time}</div>
          <div class="tekst">
            <div class="naam">${e.name}</div>
            <div class="sub">${Qe(e,t)}</div>
          </div>
        </button>
        <button
          class="schakelaar"
          role="switch"
          aria-checked=${n?"true":"false"}
          aria-label="Wekker ${e.name} aan of uit"
          @click=${()=>this._zetAan(e,!n)}
        ></button>
        <button
          class="icoonknop"
          title="Meer"
          aria-label="Meer voor ${e.name}"
          aria-haspopup="menu"
          aria-expanded=${this._menuVoor===e.id?"true":"false"}
          @click=${o=>this._wisselMenu(e,o)}
        >
          ${J(Wt)}
        </button>
        ${this._menuVoor===e.id?p`<div
              class="menu ${this._menuPositie?"":"meten"}"
              role="menu"
              style=${this._menuPositie?`left:${this._menuPositie.left}px;top:${this._menuPositie.top}px`:""}
            >
              <button role="menuitem" @click=${()=>this._overslaan(e)}>
                ${e.skip_next?"Toch niet overslaan":"Overslaan"}
              </button>
              <button
                role="menuitem"
                @click=${()=>{this._sluitMenu(),this._bevestigVoor=e.id}}
              >
                Verwijderen
              </button>
            </div>`:d}
      </div>
      ${this._bevestigVoor===e.id?p`<div class="onderrij">
            <span class="boodschap">
              Wekker "${e.name}" van ${e.time} verwijderen?
            </span>
            <button
              class="tekstknop"
              @click=${()=>{this._bevestigVoor=null}}
            >
              Annuleren
            </button>
            <button
              class="tekstknop gevaar"
              @click=${()=>this._verwijder(e)}
            >
              Verwijderen
            </button>
          </div>`:d}
      ${i?p`<div class="onderrij ${i.isFout?"fout":""}">
            ${J(i.isFout?Gt:it,"icoon klein")}
            <span class="boodschap">${i.tekst}</span>
            <button class="tekstknop" @click=${()=>this._begrepen(e)}>
              Begrepen
            </button>
          </div>`:d}
    `}};v(K,"properties",{hass:{attribute:!1},_config:{state:!0},_toestand:{state:!0},_fout:{state:!0},_menuVoor:{state:!0},_menuPositie:{state:!0},_bevestigVoor:{state:!0},_bezig:{state:!0},_tijdelijkeMelding:{state:!0},_editorVoor:{state:!0},_entiteiten:{state:!0}}),v(K,"styles",C`
    /* unsafeCSS en niet de constante rechtstreeks: lit weigert een gewone
       string in een css-template en gooit dan — op modulescope, wat SPEC 19.4
       verbiedt. De waarde is onze eigen constante en komt nergens van buiten. */
    :host {
      --domotiapp-accent: ${z(F)};
    }
    /* Geen overflow:hidden op de kaart. Sinds fase 6b staat het overloopmenu
       position:fixed en zou een gewone overflow het niet meer knippen, maar de
       reden blijft staan voor alles wat er nog bij kan komen — en de stopknop houdt
       daarom zijn eigen hoekafronding. */
    .sluiter {
      position: fixed;
      inset: 0;
      z-index: 2;
    }
    .mededeling {
      padding: 16px;
      color: var(--secondary-text-color);
      font-size: var(--ha-font-size-m, 14px);
    }
    .mededeling.fout {
      color: var(--error-color);
    }

    /* --- de lijst --- */
    .rij {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      border-bottom: 1px solid var(--divider-color);
    }
    button.tikvlak {
      display: flex;
      align-items: center;
      gap: 12px;
      flex: 1;
      min-width: 0;
      border: none;
      background: none;
      padding: 0;
      margin: 0;
      cursor: pointer;
      text-align: left;
      font-family: inherit;
      color: inherit;
    }
    .tijd {
      font-size: 28px;
      line-height: 1.1;
      font-weight: 400;
      color: var(--primary-text-color);
      font-variant-numeric: tabular-nums;
      min-width: 82px;
    }
    /* De onderste regel van de kaart krijgt geen streep: er staat niets onder om
       van te scheiden. Sinds de kopbalk boven staat is dat de laatste wekkerrij, en
       niet meer de voetregel die er toen achter kwam. */
    .rij:last-child,
    .onderrij:last-child {
      border-bottom: none;
    }
    .rij.uit .tijd,
    .rij.uit .naam {
      color: var(--secondary-text-color);
    }
    .tekst {
      flex: 1;
      min-width: 0;
    }
    .naam {
      color: var(--primary-text-color);
      font-size: var(--ha-font-size-m, 14px);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .sub {
      color: var(--secondary-text-color);
      font-size: var(--ha-font-size-s, 12px);
    }

    /* --- de schakelaar; eigen knop, zie de kop van dit bestand --- */
    .schakelaar {
      flex: 0 0 auto;
      width: 44px;
      height: 24px;
      border-radius: 12px;
      border: none;
      padding: 0;
      cursor: pointer;
      position: relative;
      background: var(--disabled-text-color, #9e9e9e);
      transition: background 0.2s ease;
    }
    .schakelaar[aria-checked="true"] {
      background: var(--domotiapp-accent);
    }
    .schakelaar::after {
      content: "";
      position: absolute;
      top: 2px;
      left: 2px;
      width: 20px;
      height: 20px;
      border-radius: 50%;
      background: var(--card-background-color, #fff);
      transition: transform 0.2s ease;
    }
    .schakelaar[aria-checked="true"]::after {
      transform: translateX(20px);
    }

    /* --- knoppen en iconen --- */
    button.icoonknop {
      flex: 0 0 auto;
      width: 40px;
      height: 40px;
      border: none;
      border-radius: 50%;
      background: none;
      cursor: pointer;
      color: var(--secondary-text-color);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 0;
    }
    button.icoonknop:hover {
      background: var(--divider-color);
    }
    .icoon {
      width: 24px;
      height: 24px;
      fill: currentColor;
    }
    .icoon.klein {
      width: 18px;
      height: 18px;
      flex: 0 0 auto;
    }

    /* --- overloopmenu ---
       position:fixed en niet absolute: als absolute laag in de rij stond het menu
       altijd 40 px onder de knop, en bij de onderste rij stak het daarmee onder de
       kaart uit — over wat er op het dashboard onder stond. Dat is de bevinding van
       fase 6b. Met fixed bepaalt plaatsMenu() de plek, en die klapt het menu boven
       de knop zodra het er onder niet binnen de kaart past.

       De klasse "meten" is het beeld vóór die berekening: het menu moet gerenderd
       zijn om zijn hoogte te kunnen meten, maar het hoort niet één beeldopbouw lang
       links bovenin te staan. Daarom visibility en niet display:none — een element
       zonder layout heeft geen afmetingen om te meten. */
    .menu {
      position: fixed;
      left: 0;
      top: 0;
      z-index: 3;
      min-width: 168px;
      background: var(--card-background-color, #fff);
      border: 1px solid var(--divider-color);
      border-radius: 8px;
      box-shadow: 0 2px 12px rgba(0, 0, 0, 0.28);
      overflow: hidden;
    }
    .menu.meten {
      visibility: hidden;
    }
    .menu button {
      display: block;
      width: 100%;
      text-align: left;
      padding: 12px 16px;
      border: none;
      background: none;
      cursor: pointer;
      color: var(--primary-text-color);
      font-size: var(--ha-font-size-m, 14px);
      font-family: inherit;
    }
    .menu button:hover {
      background: var(--divider-color);
    }

    /* --- melding en bevestiging op een rij --- */
    .onderrij {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 0 16px 12px 16px;
      border-bottom: 1px solid var(--divider-color);
      font-size: var(--ha-font-size-s, 12px);
    }
    .onderrij .boodschap {
      flex: 1;
      color: var(--secondary-text-color);
    }
    .onderrij.fout .boodschap,
    .onderrij.fout .icoon {
      color: var(--error-color);
    }
    button.tekstknop {
      border: 1px solid var(--divider-color);
      border-radius: 16px;
      background: none;
      color: var(--primary-text-color);
      padding: 6px 14px;
      cursor: pointer;
      font-size: var(--ha-font-size-s, 12px);
      font-family: inherit;
      white-space: nowrap;
    }
    button.tekstknop:hover {
      background: var(--divider-color);
    }
    button.tekstknop.gevaar {
      color: var(--error-color);
      border-color: var(--error-color);
    }

    /* --- kopbalk (SPEC 3.1 en 3.2) ---
       Bovenaan sinds fase 6b: met tien wekkers stonden de eerstvolgende wektijd en
       de plusknop onder de vouw. Bij een lege lijst is dit de hele kaart en hoort er
       geen scheidingslijn onder — er staat niets om van te scheiden. */
    .kop {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      color: var(--secondary-text-color);
      font-size: var(--ha-font-size-m, 14px);
      border-bottom: 1px solid var(--divider-color);
    }
    .kop.leeg {
      border-bottom: none;
    }
    .kop .volgende {
      flex: 1;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    /* --- de stoptoestand (SPEC 4) --- */
    button.stopknop {
      display: block;
      width: 100%;
      border: none;
      border-radius: var(--ha-card-border-radius, 12px);
      cursor: pointer;
      background: var(--domotiapp-accent);
      color: #fff;
      padding: 32px 16px;
      font-family: inherit;
      text-align: center;
    }
    .stopknop .stop-tijd {
      font-size: 44px;
      line-height: 1.1;
      font-variant-numeric: tabular-nums;
    }
    .stopknop .stop-naam {
      font-size: var(--ha-font-size-l, 16px);
      opacity: 0.9;
      margin-top: 4px;
    }
    .stopknop .stop-woord {
      margin-top: 20px;
      font-size: 24px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }
  `);var N=class N extends g{constructor(){super(...arguments);v(this,"_label",t=>t.name==="person"?"Persoon":t.name)}setConfig(t){this._config={...t}}render(){return!this._config||!this.hass?d:p`
      <div class="uitleg">
        Elke persoon heeft zijn eigen wekkerlijst. De kaart toont alleen de
        wekkers van de gekozen persoon.
      </div>
      <ha-form
        .hass=${this.hass}
        .data=${this._config}
        .schema=${N._SCHEMA}
        .computeLabel=${this._label}
        @value-changed=${this._gewijzigd}
      ></ha-form>
    `}_gewijzigd(t){t.stopPropagation();let i={...this._config,...t.detail.value};this.dispatchEvent(new CustomEvent("config-changed",{detail:{config:i},bubbles:!0,composed:!0}))}};v(N,"properties",{hass:{attribute:!1},_config:{state:!0}}),v(N,"styles",C`
    .uitleg {
      padding: 0 0 12px 0;
      color: var(--secondary-text-color);
      font-size: var(--ha-font-size-s, 12px);
    }
  `),v(N,"_SCHEMA",[{name:"person",required:!0,selector:{entity:{filter:{domain:"person"}}}}]);var me=N;Je({leesRegistry:()=>globalThis.customElements,definities:[[x,K],[he,me],[Ne,T]],waarschuw:s=>console.warn(`${x}: ${s}`)});window.customCards=window.customCards||[];window.customCards.some(s=>s.type===x)||window.customCards.push({type:x,name:Ve,description:`Wekkerkaart van DomotiApp (v${It}).`,preview:!1,documentationURL:Oe});
