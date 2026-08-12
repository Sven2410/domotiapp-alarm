var it=Object.defineProperty;var st=(n,e,t)=>e in n?it(n,e,{enumerable:!0,configurable:!0,writable:!0,value:t}):n[e]=t;var b=(n,e,t)=>st(n,typeof e!="symbol"?e+"":e,t);var K=globalThis,G=K.ShadowRoot&&(K.ShadyCSS===void 0||K.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,X=Symbol(),fe=new WeakMap,V=class{constructor(e,t,i){if(this._$cssResult$=!0,i!==X)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o,t=this.t;if(G&&e===void 0){let i=t!==void 0&&t.length===1;i&&(e=fe.get(t)),e===void 0&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),i&&fe.set(t,e))}return e}toString(){return this.cssText}},z=n=>new V(typeof n=="string"?n:n+"",void 0,X),S=(n,...e)=>{let t=n.length===1?n[0]:e.reduce((i,s,o)=>i+(r=>{if(r._$cssResult$===!0)return r.cssText;if(typeof r=="number")return r;throw Error("Value passed to 'css' function must be a 'css' function result: "+r+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(s)+n[o+1],n[0]);return new V(t,n,X)},ve=(n,e)=>{if(G)n.adoptedStyleSheets=e.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(let t of e){let i=document.createElement("style"),s=K.litNonce;s!==void 0&&i.setAttribute("nonce",s),i.textContent=t.cssText,n.appendChild(i)}},Q=G?n=>n:n=>n instanceof CSSStyleSheet?(e=>{let t="";for(let i of e.cssRules)t+=i.cssText;return z(t)})(n):n;var{is:ot,defineProperty:rt,getOwnPropertyDescriptor:at,getOwnPropertyNames:dt,getOwnPropertySymbols:lt,getPrototypeOf:pt}=Object,B=globalThis,be=B.trustedTypes,ht=be?be.emptyScript:"",ct=B.reactiveElementPolyfillSupport,D=(n,e)=>n,ee={toAttribute(n,e){switch(e){case Boolean:n=n?ht:null;break;case Object:case Array:n=n==null?n:JSON.stringify(n)}return n},fromAttribute(n,e){let t=n;switch(e){case Boolean:t=n!==null;break;case Number:t=n===null?null:Number(n);break;case Object:case Array:try{t=JSON.parse(n)}catch{t=null}}return t}},ke=(n,e)=>!ot(n,e),_e={attribute:!0,type:String,converter:ee,reflect:!1,useDefault:!1,hasChanged:ke};Symbol.metadata??=Symbol("metadata"),B.litPropertyMetadata??=new WeakMap;var k=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??=[]).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=_e){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){let i=Symbol(),s=this.getPropertyDescriptor(e,i,t);s!==void 0&&rt(this.prototype,e,s)}}static getPropertyDescriptor(e,t,i){let{get:s,set:o}=at(this.prototype,e)??{get(){return this[t]},set(r){this[t]=r}};return{get:s,set(r){let h=s?.call(this);o?.call(this,r),this.requestUpdate(e,h,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??_e}static _$Ei(){if(this.hasOwnProperty(D("elementProperties")))return;let e=pt(this);e.finalize(),e.l!==void 0&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(D("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(D("properties"))){let t=this.properties,i=[...dt(t),...lt(t)];for(let s of i)this.createProperty(s,t[s])}let e=this[Symbol.metadata];if(e!==null){let t=litPropertyMetadata.get(e);if(t!==void 0)for(let[i,s]of t)this.elementProperties.set(i,s)}this._$Eh=new Map;for(let[t,i]of this.elementProperties){let s=this._$Eu(t,i);s!==void 0&&this._$Eh.set(s,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){let t=[];if(Array.isArray(e)){let i=new Set(e.flat(1/0).reverse());for(let s of i)t.unshift(Q(s))}else e!==void 0&&t.push(Q(e));return t}static _$Eu(e,t){let i=t.attribute;return i===!1?void 0:typeof i=="string"?i:typeof e=="string"?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(e=>this.enableUpdating=e),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(e=>e(this))}addController(e){(this._$EO??=new Set).add(e),this.renderRoot!==void 0&&this.isConnected&&e.hostConnected?.()}removeController(e){this._$EO?.delete(e)}_$E_(){let e=new Map,t=this.constructor.elementProperties;for(let i of t.keys())this.hasOwnProperty(i)&&(e.set(i,this[i]),delete this[i]);e.size>0&&(this._$Ep=e)}createRenderRoot(){let e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return ve(e,this.constructor.elementStyles),e}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(e=>e.hostConnected?.())}enableUpdating(e){}disconnectedCallback(){this._$EO?.forEach(e=>e.hostDisconnected?.())}attributeChangedCallback(e,t,i){this._$AK(e,i)}_$ET(e,t){let i=this.constructor.elementProperties.get(e),s=this.constructor._$Eu(e,i);if(s!==void 0&&i.reflect===!0){let o=(i.converter?.toAttribute!==void 0?i.converter:ee).toAttribute(t,i.type);this._$Em=e,o==null?this.removeAttribute(s):this.setAttribute(s,o),this._$Em=null}}_$AK(e,t){let i=this.constructor,s=i._$Eh.get(e);if(s!==void 0&&this._$Em!==s){let o=i.getPropertyOptions(s),r=typeof o.converter=="function"?{fromAttribute:o.converter}:o.converter?.fromAttribute!==void 0?o.converter:ee;this._$Em=s;let h=r.fromAttribute(t,o.type);this[s]=h??this._$Ej?.get(s)??h,this._$Em=null}}requestUpdate(e,t,i,s=!1,o){if(e!==void 0){let r=this.constructor;if(s===!1&&(o=this[e]),i??=r.getPropertyOptions(e),!((i.hasChanged??ke)(o,t)||i.useDefault&&i.reflect&&o===this._$Ej?.get(e)&&!this.hasAttribute(r._$Eu(e,i))))return;this.C(e,t,i)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(e,t,{useDefault:i,reflect:s,wrapped:o},r){i&&!(this._$Ej??=new Map).has(e)&&(this._$Ej.set(e,r??t??this[e]),o!==!0||r!==void 0)||(this._$AL.has(e)||(this.hasUpdated||i||(t=void 0),this._$AL.set(e,t)),s===!0&&this._$Em!==e&&(this._$Eq??=new Set).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}let e=this.scheduleUpdate();return e!=null&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[s,o]of this._$Ep)this[s]=o;this._$Ep=void 0}let i=this.constructor.elementProperties;if(i.size>0)for(let[s,o]of i){let{wrapped:r}=o,h=this[s];r!==!0||this._$AL.has(s)||h===void 0||this.C(s,void 0,o,h)}}let e=!1,t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),this._$EO?.forEach(i=>i.hostUpdate?.()),this.update(t)):this._$EM()}catch(i){throw e=!1,this._$EM(),i}e&&this._$AE(t)}willUpdate(e){}_$AE(e){this._$EO?.forEach(t=>t.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&=this._$Eq.forEach(t=>this._$ET(t,this[t])),this._$EM()}updated(e){}firstUpdated(e){}};k.elementStyles=[],k.shadowRootOptions={mode:"open"},k[D("elementProperties")]=new Map,k[D("finalized")]=new Map,ct?.({ReactiveElement:k}),(B.reactiveElementVersions??=[]).push("2.1.2");var ae=globalThis,xe=n=>n,Z=ae.trustedTypes,$e=Z?Z.createPolicy("lit-html",{createHTML:n=>n}):void 0,ze="$lit$",$=`lit$${Math.random().toFixed(9).slice(2)}$`,Se="?"+$,ut=`<${Se}>`,A=document,M=()=>A.createComment(""),P=n=>n===null||typeof n!="object"&&typeof n!="function",de=Array.isArray,gt=n=>de(n)||typeof n?.[Symbol.iterator]=="function",te=`[ 	
\f\r]`,H=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,ye=/-->/g,we=/>/g,y=RegExp(`>|${te}(?:([^\\s"'>=/]+)(${te}*=${te}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),Ae=/'/g,Ee=/"/g,Ce=/^(?:script|style|textarea|title)$/i,le=n=>(e,...t)=>({_$litType$:n,strings:e,values:t}),p=le(1),qt=le(2),Yt=le(3),E=Symbol.for("lit-noChange"),l=Symbol.for("lit-nothing"),je=new WeakMap,w=A.createTreeWalker(A,129);function Te(n,e){if(!de(n)||!n.hasOwnProperty("raw"))throw Error("invalid template strings array");return $e!==void 0?$e.createHTML(e):e}var mt=(n,e)=>{let t=n.length-1,i=[],s,o=e===2?"<svg>":e===3?"<math>":"",r=H;for(let h=0;h<t;h++){let d=n[h],a,u,c=-1,g=0;for(;g<d.length&&(r.lastIndex=g,u=r.exec(d),u!==null);)g=r.lastIndex,r===H?u[1]==="!--"?r=ye:u[1]!==void 0?r=we:u[2]!==void 0?(Ce.test(u[2])&&(s=RegExp("</"+u[2],"g")),r=y):u[3]!==void 0&&(r=y):r===y?u[0]===">"?(r=s??H,c=-1):u[1]===void 0?c=-2:(c=r.lastIndex-u[2].length,a=u[1],r=u[3]===void 0?y:u[3]==='"'?Ee:Ae):r===Ee||r===Ae?r=y:r===ye||r===we?r=H:(r=y,s=void 0);let m=r===y&&n[h+1].startsWith("/>")?" ":"";o+=r===H?d+ut:c>=0?(i.push(a),d.slice(0,c)+ze+d.slice(c)+$+m):d+$+(c===-2?h:m)}return[Te(n,o+(n[t]||"<?>")+(e===2?"</svg>":e===3?"</math>":"")),i]},R=class n{constructor({strings:e,_$litType$:t},i){let s;this.parts=[];let o=0,r=0,h=e.length-1,d=this.parts,[a,u]=mt(e,t);if(this.el=n.createElement(a,i),w.currentNode=this.el.content,t===2||t===3){let c=this.el.content.firstChild;c.replaceWith(...c.childNodes)}for(;(s=w.nextNode())!==null&&d.length<h;){if(s.nodeType===1){if(s.hasAttributes())for(let c of s.getAttributeNames())if(c.endsWith(ze)){let g=u[r++],m=s.getAttribute(c).split($),j=/([.?@])?(.*)/.exec(g);d.push({type:1,index:o,name:j[2],strings:m,ctor:j[1]==="."?ie:j[1]==="?"?se:j[1]==="@"?oe:T}),s.removeAttribute(c)}else c.startsWith($)&&(d.push({type:6,index:o}),s.removeAttribute(c));if(Ce.test(s.tagName)){let c=s.textContent.split($),g=c.length-1;if(g>0){s.textContent=Z?Z.emptyScript:"";for(let m=0;m<g;m++)s.append(c[m],M()),w.nextNode(),d.push({type:2,index:++o});s.append(c[g],M())}}}else if(s.nodeType===8)if(s.data===Se)d.push({type:2,index:o});else{let c=-1;for(;(c=s.data.indexOf($,c+1))!==-1;)d.push({type:7,index:o}),c+=$.length-1}o++}}static createElement(e,t){let i=A.createElement("template");return i.innerHTML=e,i}};function C(n,e,t=n,i){if(e===E)return e;let s=i!==void 0?t._$Co?.[i]:t._$Cl,o=P(e)?void 0:e._$litDirective$;return s?.constructor!==o&&(s?._$AO?.(!1),o===void 0?s=void 0:(s=new o(n),s._$AT(n,t,i)),i!==void 0?(t._$Co??=[])[i]=s:t._$Cl=s),s!==void 0&&(e=C(n,s._$AS(n,e.values),s,i)),e}var ne=class{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){let{el:{content:t},parts:i}=this._$AD,s=(e?.creationScope??A).importNode(t,!0);w.currentNode=s;let o=w.nextNode(),r=0,h=0,d=i[0];for(;d!==void 0;){if(r===d.index){let a;d.type===2?a=new L(o,o.nextSibling,this,e):d.type===1?a=new d.ctor(o,d.name,d.strings,this,e):d.type===6&&(a=new re(o,this,e)),this._$AV.push(a),d=i[++h]}r!==d?.index&&(o=w.nextNode(),r++)}return w.currentNode=A,s}p(e){let t=0;for(let i of this._$AV)i!==void 0&&(i.strings!==void 0?(i._$AI(e,i,t),t+=i.strings.length-2):i._$AI(e[t])),t++}},L=class n{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(e,t,i,s){this.type=2,this._$AH=l,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=i,this.options=s,this._$Cv=s?.isConnected??!0}get parentNode(){let e=this._$AA.parentNode,t=this._$AM;return t!==void 0&&e?.nodeType===11&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=C(this,e,t),P(e)?e===l||e==null||e===""?(this._$AH!==l&&this._$AR(),this._$AH=l):e!==this._$AH&&e!==E&&this._(e):e._$litType$!==void 0?this.$(e):e.nodeType!==void 0?this.T(e):gt(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==l&&P(this._$AH)?this._$AA.nextSibling.data=e:this.T(A.createTextNode(e)),this._$AH=e}$(e){let{values:t,_$litType$:i}=e,s=typeof i=="number"?this._$AC(e):(i.el===void 0&&(i.el=R.createElement(Te(i.h,i.h[0]),this.options)),i);if(this._$AH?._$AD===s)this._$AH.p(t);else{let o=new ne(s,this),r=o.u(this.options);o.p(t),this.T(r),this._$AH=o}}_$AC(e){let t=je.get(e.strings);return t===void 0&&je.set(e.strings,t=new R(e)),t}k(e){de(this._$AH)||(this._$AH=[],this._$AR());let t=this._$AH,i,s=0;for(let o of e)s===t.length?t.push(i=new n(this.O(M()),this.O(M()),this,this.options)):i=t[s],i._$AI(o),s++;s<t.length&&(this._$AR(i&&i._$AB.nextSibling,s),t.length=s)}_$AR(e=this._$AA.nextSibling,t){for(this._$AP?.(!1,!0,t);e!==this._$AB;){let i=xe(e).nextSibling;xe(e).remove(),e=i}}setConnected(e){this._$AM===void 0&&(this._$Cv=e,this._$AP?.(e))}},T=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,i,s,o){this.type=1,this._$AH=l,this._$AN=void 0,this.element=e,this.name=t,this._$AM=s,this.options=o,i.length>2||i[0]!==""||i[1]!==""?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=l}_$AI(e,t=this,i,s){let o=this.strings,r=!1;if(o===void 0)e=C(this,e,t,0),r=!P(e)||e!==this._$AH&&e!==E,r&&(this._$AH=e);else{let h=e,d,a;for(e=o[0],d=0;d<o.length-1;d++)a=C(this,h[i+d],t,d),a===E&&(a=this._$AH[d]),r||=!P(a)||a!==this._$AH[d],a===l?e=l:e!==l&&(e+=(a??"")+o[d+1]),this._$AH[d]=a}r&&!s&&this.j(e)}j(e){e===l?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}},ie=class extends T{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===l?void 0:e}},se=class extends T{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==l)}},oe=class extends T{constructor(e,t,i,s,o){super(e,t,i,s,o),this.type=5}_$AI(e,t=this){if((e=C(this,e,t,0)??l)===E)return;let i=this._$AH,s=e===l&&i!==l||e.capture!==i.capture||e.once!==i.once||e.passive!==i.passive,o=e!==l&&(i===l||s);s&&this.element.removeEventListener(this.name,this,i),o&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,e):this._$AH.handleEvent(e)}},re=class{constructor(e,t,i){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(e){C(this,e)}};var ft=ae.litHtmlPolyfillSupport;ft?.(R,L),(ae.litHtmlVersions??=[]).push("3.3.3");var Oe=(n,e,t)=>{let i=t?.renderBefore??e,s=i._$litPart$;if(s===void 0){let o=t?.renderBefore??null;i._$litPart$=s=new L(e.insertBefore(M(),o),o,void 0,t??{})}return s._$AI(n),s};var pe=globalThis,v=class extends k{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let e=super.createRenderRoot();return this.renderOptions.renderBefore??=e.firstChild,e}update(e){let t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=Oe(t,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return E}};v._$litElement$=!0,v.finalized=!0,pe.litElementHydrateSupport?.({LitElement:v});var vt=pe.litElementPolyfillSupport;vt?.({LitElement:v});(pe.litElementVersions??=[]).push("4.2.2");var x="domotiapp-alarm-card",he="domotiapp-alarm-card-editor",Ne="domotiapp-alarm-editor",Ve="DomotiApp Alarm",De="https://github.com/Sven2410/domotiapp-alarm",_="domotiapp_alarm",f=Object.freeze({get:`${_}/alarms/get`,save:`${_}/alarms/save`,setEnabled:`${_}/alarms/set_enabled`,delete:`${_}/alarms/delete`,stop:`${_}/alarms/stop`,clearMessage:`${_}/alarms/clear_message`,search:`${_}/sound/search`,entities:`${_}/entities/list`,previewStart:`${_}/preview/start`,subscribe:`${_}/updates/subscribe`}),F="#026FA1";function He(n){let e=typeof n?.name=="string"?n.name.trim():"",t=typeof n?.time=="string"?n.time.trim():"";return e&&t?`Wil je de wekker "${e}" van ${t} verwijderen?`:e?`Wil je de wekker "${e}" verwijderen?`:t?`Wil je de wekker van ${t} verwijderen?`:"Wil je deze wekker verwijderen?"}var bt="07:00";var _t=["uri","name","media_type","image"],kt="Let op: deze tijd bestaat twee nachten per jaar niet, of twee keer. Bij de overgang naar zomertijd wordt het uur van 02:00 tot 03:00 overgeslagen; die nacht gaat deze wekker niet af. Bij de overgang naar wintertijd komt dat uur twee keer voorbij; die nacht gaat hij twee keer af. Kies een tijd v\xF3\xF3r 02:00 of n\xE1 03:00 als dat een probleem is.",xt="Dit geluid stopt van zichzelf. Een los nummer is na een paar minuten voorbij; daarna is het stil. Kies een afspeellijst of een radiostation als de wekker moet blijven spelen tot je hem uitzet.";var $t="Music Assistant Wekker",yt="Verlichting Wekker";function q(){return{id:null,name:"",time:bt,days:[],enabled:!0,sound:null,endless:null,speaker:"",volume_pct:40,light:null}}function Me(n){let e=q();return!n||typeof n!="object"?e:{id:typeof n.id=="string"?n.id:null,name:typeof n.name=="string"?n.name:"",time:ce(n.time)?n.time:e.time,days:Array.isArray(n.days)?[...n.days]:[],enabled:n.enabled!==!1,sound:U(n.sound),endless:null,speaker:typeof n.speaker=="string"?n.speaker:"",volume_pct:Number.isInteger(n.volume_pct)?n.volume_pct:e.volume_pct,light:n.light&&typeof n.light=="object"?{entity_id:n.light.entity_id,brightness_pct:Number.isInteger(n.light.brightness_pct)?n.light.brightness_pct:60}:null}}function U(n){if(!n||typeof n!="object"||Array.isArray(n)||typeof n.uri!="string"||!n.uri)return null;let e={};for(let t of _t)e[t]=n[t]===void 0?null:n[t];return e}function ce(n){if(typeof n!="string"||n.length!==5||n[2]!==":")return!1;let e=Number(n.slice(0,2)),t=Number(n.slice(3));return!/^\d\d$/.test(n.slice(0,2))||!/^\d\d$/.test(n.slice(3))?!1:e>=0&&e<=23&&t>=0&&t<=59}function ue(n){let e=[];return!n||typeof n!="object"?{ok:!1,ontbreekt:["alles"]}:((typeof n.name!="string"||!n.name.trim())&&e.push("een naam"),ce(n.time)||e.push("een geldige tijd"),n.speaker||e.push("een speaker"),(!n.sound||!n.sound.uri)&&e.push("een geluid"),(!Number.isInteger(n.volume_pct)||n.volume_pct<1||n.volume_pct>100)&&e.push("een volume tussen 1 en 100"),{ok:e.length===0,ontbreekt:e})}function Pe(n){let e={name:(n.name||"").trim(),time:n.time,days:[...new Set(n.days||[])].sort((t,i)=>t-i),enabled:n.enabled!==!1,sound:U(n.sound),speaker:n.speaker,volume_pct:n.volume_pct,light:n.light?{entity_id:n.light.entity_id,brightness_pct:n.light.brightness_pct}:null};return n.id&&(e.id=n.id),e}function Re(n,e){let t=new Set(n||[]);return t.has(e)?t.delete(e):t.add(e),[...t].sort((i,s)=>i-s)}function Le(n){return ce(n)&&n.slice(0,2)==="02"?kt:null}function Ue(n){return n===!1?xt:null}function Ie(n){return typeof n?.endless=="boolean"?n.endless:null}function Y(n,e){let t=e==="lamp",i=t?yt:$t,s=t?"lampen":"speakers";return!n||typeof n!="object"?`De lijst met ${s} is niet op te halen.`:n.label_exists===!1?`Het label '${i}' bestaat nog niet. De beheerder moet dat label aanmaken en op de ${s} zetten die als wekker mogen dienen.`:Array.isArray(n.entities)&&n.entities.length>0?null:Number(n.filtered_out)>0?t?`De entiteiten met het label '${i}' zijn geen lampen.`:"De gelabelde speakers zijn geen Music Assistant-speakers, of ze kunnen geen volume instellen.":`Er zijn nog geen ${s} met het label '${i}'.`}function We(n,e){return Y(e,"speaker")!==null?!1:ue(n).ok}var At=[[1,"ma"],[2,"di"],[3,"wo"],[4,"do"],[5,"vr"],[6,"za"],[7,"zo"]],Et=[["","Alles"],["playlist","Afspeellijsten"],["radio","Radio"],["artist","Artiesten"],["album","Albums"],["track","Nummers"],["podcast","Podcasts"]],I="M13,9H11V7H13M13,17H11V11H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z",jt="M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z",zt="M6,2H18V8H18V8L14,12L18,16V16H18V22H6V16H6V16L10,12L6,8V8H6V2M16,16.5L12,12.5L8,16.5V20H16V16.5M12,11.5L16,7.5V4H8V7.5L12,11.5Z",O=class extends v{constructor(){super(),this._concept=q(),this._zoekterm="",this._soort="",this._treffers=null,this._zoekt=!1,this._melding=null,this._speelt=!1,this._bezig=!1,this._afmeldenVoorbeeld=null,this._opEscape=e=>{e.key==="Escape"&&this._annuleren()}}connectedCallback(){super.connectedCallback(),window.addEventListener("keydown",this._opEscape,!0)}disconnectedCallback(){super.disconnectedCallback(),window.removeEventListener("keydown",this._opEscape,!0),this._stopVoorbeeld()}willUpdate(e){e.has("wekker")&&(this._concept=this.wekker?Me(this.wekker):q(),this._treffers=null,this._zoekterm="",this._melding=null)}_zet(e){this._concept={...this._concept,...e}}async _startVoorbeeld(){if(!(this._speelt||!this.hass)){if(!this._concept.speaker||!this._concept.sound){this._melding={tekst:"Kies eerst een speaker en een geluid.",fout:!0};return}this._melding=null;try{this._afmeldenVoorbeeld=await this.hass.connection.subscribeMessage(()=>{},{type:f.previewStart,speaker:this._concept.speaker,sound:U(this._concept.sound),volume_pct:this._concept.volume_pct,light:this._concept.light??null}),this._speelt=!0}catch(e){this._melding={tekst:e?.message??"Het voorbeeld kon niet starten.",fout:!0}}}}_stopVoorbeeld(){if(this._afmeldenVoorbeeld){try{this._afmeldenVoorbeeld()}catch(e){console.warn(`domotiapp-alarm-editor: afmelden mislukt: ${e?.message??e}`)}this._afmeldenVoorbeeld=null}this._speelt=!1}async _zoek(){let e=(this._zoekterm||"").trim();if(!(!e||!this.hass)){this._zoekt=!0,this._melding=null;try{let t={type:f.search,query:e,limit:20};this._soort&&(t.media_types=[this._soort]);let i=await this.hass.callWS(t);this._treffers=i.results??[]}catch(t){this._treffers=[],this._melding={tekst:t?.message??"Zoeken is mislukt.",fout:!0}}finally{this._zoekt=!1}}}_kiesGeluid(e){this._zet({sound:U(e),endless:Ie(e)}),this._treffers=null}async _opslaan(){if(this._bezig||!this.hass)return;let e=ue(this._concept);if(!e.ok){this._melding={tekst:`Er ontbreekt nog ${e.ontbreekt.join(", ")}.`,fout:!0};return}this._bezig=!0;try{let t=await this.hass.callWS({type:f.save,person:this.person,alarm:Pe(this._concept)});this._stopVoorbeeld(),this.dispatchEvent(new CustomEvent("editor-opgeslagen",{detail:{toestand:t},bubbles:!0,composed:!0}))}catch(t){this._melding={tekst:t?.message??"Opslaan is mislukt.",fout:!0}}finally{this._bezig=!1}}_annuleren(){this._stopVoorbeeld(),this.dispatchEvent(new CustomEvent("editor-dicht",{bubbles:!0,composed:!0}))}_svg(e){return p`<svg class="icoon" viewBox="0 0 24 24" aria-hidden="true">
      <path d=${e} />
    </svg>`}render(){if(!this.hass)return l;let e=this._concept,t=this.entiteiten?.speakers,i=this.entiteiten?.lights,s=Y(t,"speaker"),o=Y(i,"lamp"),r=Le(e.time),h=Ue(e.endless),d=We(e,t);return p`
      <div class="kop">
        <h2>${e.id?"Wekker bewerken":"Nieuwe wekker"}</h2>
      </div>

      <div class="blok">
        <label class="veld" for="tijd">Tijd</label>
        <div class="vak tijd">
          <input
            id="tijd"
            type="time"
            .value=${e.time}
            required
            @input=${a=>this._zet({time:a.target.value})}
          />
        </div>
        ${r?p`<div class="waarschuwing">
              ${this._svg(I)}<span>${r}</span>
            </div>`:l}
      </div>

      <div class="blok">
        <label class="veld">Herhaling</label>
        <div class="dagen">
          ${At.map(([a,u])=>p`<button
              type="button"
              aria-pressed=${e.days.includes(a)?"true":"false"}
              aria-label=${u}
              @click=${()=>this._zet({days:Re(e.days,a)})}
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
        <div class="vak">
          <input
            id="naam"
            type="text"
            .value=${e.name}
            placeholder="Bijvoorbeeld: Werk"
            @input=${a=>this._zet({name:a.target.value})}
          />
        </div>
      </div>

      <div class="blok">
        <label class="veld" for="speaker">Speaker</label>
        ${s?p`<div class="uitleg">${this._svg(I)}<span>${s}</span></div>`:p`<div class="vak">
              <select
                id="speaker"
                .value=${e.speaker}
                @change=${a=>this._zet({speaker:a.target.value})}
              >
                <option value="">Kies een speaker…</option>
                ${(t?.entities??[]).map(a=>p`<option value=${a.entity_id} ?selected=${a.entity_id===e.speaker}>
                    ${a.name}
                  </option>`)}
              </select>
            </div>`}
      </div>

      <div class="blok">
        <label class="veld" for="zoek">Geluid</label>
        ${e.sound?p`<div class="gekozen">
              ${e.sound.image?p`<img src=${e.sound.image} alt="" />`:l}
              <span>${e.sound.name||e.sound.uri}</span>
              <span class="soort" style="margin-left:auto">${e.sound.media_type??""}</span>
            </div>`:l}
        <div class="rij" style="margin-top:8px">
          <div class="vak">
            <input
              id="zoek"
              type="text"
              .value=${this._zoekterm}
              placeholder="Zoek media"
              @input=${a=>{this._zoekterm=a.target.value}}
              @keydown=${a=>{a.key==="Enter"&&(a.preventDefault(),this._zoek())}}
            />
          </div>
          <div class="vak auto">
            <select
              aria-label="Soort"
              @change=${a=>{this._soort=a.target.value}}
            >
              ${Et.map(([a,u])=>p`<option value=${a}>${u}</option>`)}
            </select>
          </div>
          <button
            class="knop zoekknop"
            type="button"
            title="Zoeken"
            aria-label="Zoeken"
            ?disabled=${this._zoekt}
            @click=${()=>this._zoek()}
          >
            ${this._svg(this._zoekt?zt:jt)}
          </button>
        </div>
        ${this._treffers?p`<div class="treffers">
              ${this._treffers.length===0?p`<div class="treffer">Niets gevonden.</div>`:this._treffers.map(a=>p`<button
                      class="treffer"
                      type="button"
                      @click=${()=>this._kiesGeluid(a)}
                    >
                      ${a.image?p`<img src=${a.image} alt="" />`:l}
                      <span>${a.name}</span>
                      <span class="soort">${a.media_type??""}</span>
                    </button>`)}
            </div>`:l}
        ${h?p`<div class="waarschuwing">${this._svg(I)}<span>${h}</span></div>`:l}
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
              <div class="vak">
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
              </div>
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
                    />`:l}
            `}
      </div>

      ${this._melding?p`<div class="blok">
            <div class="waarschuwing ${this._melding.fout?"fout":""}">
              ${this._svg(I)}<span>${this._melding.tekst}</span>
            </div>
          </div>`:l}

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
          ?disabled=${!d||this._bezig}
          @click=${()=>this._opslaan()}
        >
          Opslaan
        </button>
      </div>
    `}};b(O,"properties",{hass:{attribute:!1},person:{attribute:!1},wekker:{attribute:!1},entiteiten:{attribute:!1},_concept:{state:!0},_zoekterm:{state:!0},_soort:{state:!0},_treffers:{state:!0},_zoekt:{state:!0},_melding:{state:!0},_speelt:{state:!0},_bezig:{state:!0}}),b(O,"styles",S`
    :host {
      --domotiapp-accent: ${z(F)};
      display: block;
      /* De editor meet zich aan zijn EIGEN breedte, niet aan die van het venster.
         Een kaart in een bubble pop-up is smal terwijl het venster breed is, dus
         een media query zou hier precies het verkeerde meten. Gemeten in fase 8:
         container queries worden ondersteund (CSS.supports gaf true).

         Met een naam, om dezelfde reden als bij de kaart: een naamloze query
         pakt de dichtstbijzijnde container-voorouder, en dat kan er een van HA
         zijn. */
      container: domotiapp-editor / inline-size;
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
    /* --- native invoervelden: het VAK is van ons, de CONTROL niet ---
       (fase 10, en dit is de kern van die ronde)

       De rand, de radius, de achtergrond en de padding zitten op een div.vak.
       De control erbinnen krijgt width 100% en verder GEEN padding en GEEN rand.
       Daarmee zijn zijn contentbox en zijn borderbox per constructie even breed,
       en kan hij niet breder uitvallen dan de ruimte die er is — ongeacht welk
       boxmodel de browser op dat soort control toepast.

       Waarom dat niet vanzelf spreekt. Hiervoor stond hier width 100% MET
       box-sizing border-box, padding en een rand, en dat is op Chrome
       aantoonbaar goed: gemeten 320 px getekend bij 320 px beschikbaar. iOS past
       box-sizing border-box echter NIET toe op input[type="time"]. Gemeten op de
       iPhone van de eigenaar (scherm 393 CSS px, kaart 356,4, binnenruimte 324,0):

           naamveld   (input[type=text]) eigen rand eindigt op 358,5   goed
           speaker    (select)           eigen rand eindigt op 358,5   goed
           TIJDVELD   (input[type=time]) eigen rand eindigt op 372,6   FOUT

       en uit de centrering van de cijfers volgt een veldbreedte van 348,9 px —
       precies 324 + 2*12 padding + 2*1 rand = 350. Het veld stak daarmee ~9 px
       voorbij de kaartrand, waar het werd afgeknipt: geen afgeronde rechterhoek
       meer, en de tijd 12,5 px uit het midden.

       Een max-width 100% erbij zou NIET helpen: leest de UA de width als
       contentbox, dan doet hij dat met max-width ook. Alleen padding 0 en rand 0
       op de control zelf sluit het uit. */
    .vak {
      display: block;
      padding: 10px;
      border: 1px solid var(--divider-color);
      border-radius: 6px;
      background: var(--card-background-color, #fff);
    }
    .vak.tijd {
      /* Iets meer ruimte links en rechts dan de andere velden: de cijfers zijn
         hier 24 px en gaan er anders optisch tegenaan liggen. */
      padding: 10px 12px;
    }
    /* De soortkiezer in de zoekrij is de enige die zich naar zijn inhoud voegt in
       plaats van de rij te vullen. Dan moet ook de control erin auto zijn: een
       width van 100% van een vak dat zelf auto is, is een rondje. */
    .vak.auto {
      flex: 0 0 auto;
    }
    .vak.auto select {
      width: auto;
    }
    .vak input,
    .vak select {
      display: block;
      width: 100%;
      box-sizing: border-box;
      padding: 0;
      border: 0;
      margin: 0;
      background: transparent;
      color: var(--primary-text-color);
      font-family: inherit;
      font-size: var(--ha-font-size-m, 14px);
    }
    .vak input[type="time"] {
      font-size: 24px;
      font-variant-numeric: tabular-nums;
      /* iOS centreert de waarde van een tijdveld zelf; Chrome lijnt hem links uit.
         Expliciet centreren maakt van dat verschil een keuze in plaats van een
         toevalligheid.

         Wat het NIET doet is beide platformen hetzelfde laten tonen, en dat is
         gemeten: Chrome tekent er een eigen klokknop rechts in (CSS 315,9 → 335,5)
         en centreert de waarde in wat daarvan overblijft, zodat de cijfers 19,9 px
         links van het midden van de kaart uitkomen. iOS heeft die knop niet en
         centreert wel echt. De DOOS is op beide gelijk; het beeld erbinnen niet. */
      text-align: center;
    }
    /* Onder de 300 px wordt het veld zelf smal genoeg dat de native tijdweergave
       eronder kan lijden. Dan liever kleinere cijfers dan afgesneden cijfers. */
    @container domotiapp-editor (max-width: 300px) {
      .vak input[type="time"] {
        font-size: 20px;
      }
    }
    /* De twee schuiven zijn het enige native control dat width 100% krijgt en
       GEEN vak nodig heeft: ze dragen zelf geen padding en geen rand, dus hun
       contentbox en borderbox zijn al gelijk. Gemeten: box-sizing staat hier op
       content-box en tóch is de schuif 320 px bij 320 px beschikbaar — wat laat
       zien dat het boxmodel niet de kwaal is maar de padding. Geef ze er dus ook
       nooit een. */
    input[type="range"] {
      width: 100%;
      padding: 0;
      border: 0;
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
    /* Wikkelen, om dezelfde reden als de voetregel. Gemeten in fase 8 bij een
       kaart van 244 px: het zoekveld werd tot 27 px platgeknepen tussen de
       soortkiezer (127 px) en het vergrootglas (42 px) — je zag niet meer wat je
       typte. De ondergrens van 8em zorgt dat het veld leesbaar blijft en dat de
       rest naar de volgende regel gaat in plaats van dat het veld verdwijnt. */
    .rij {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }
    .rij > :first-child {
      flex: 1 1 8em;
      min-width: 8em;
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
      /* width 100% samen met eigen padding — dezelfde vorm als het tijdveld.
         Chrome geeft een button border-box uit zijn eigen UA-stylesheet (gemeten:
         303 px getekend bij 303 px beschikbaar), maar dat is een standaard van de
         browser en geen afspraak van ons. Hier staat hij expliciet, zodat het niet
         uitmaakt wat de UA vindt. */
      box-sizing: border-box;
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
    /* De naam van een treffer is vrije tekst uit Music Assistant en heeft geen
       bovengrens; hij moet dus kunnen krimpen. Zonder deze twee regels loopt de
       rij over en duwt hij de soort naar buiten — gemeten bij een kaart van
       208 px: de badge "podcast" stak 16 px buiten de kaart en de treffer meldde
       scrollWidth 206 bij clientWidth 157. Zelfde vorm als de bevestigingsregel
       uit fase 9, nu in een toestand die niemand eerder had opengezet. */
    .treffer span:not(.soort) {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .treffer .soort {
      /* Hier stond in de eerste opzet flex 0 0 auto. De mutatieproef wees uit dat
         die regel niets doet: hem terugzetten op 0 1 auto verandert geen enkele
         positie, ook niet samen met de mutatie hierboven (beide uitkomsten waren
         tot op de tiende gelijk). De reden is de white-space hieronder — een badge
         die niet mag afbreken kan niet onder zijn tekstbreedte geknepen worden.
         Dat is exact valkuil 34, derde rij, en dezelfde bevinding als bij
         button.tekstknop in fase 9. */
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
    /* WIKKELEN, en dat is de kern van de reparatie uit fase 8.
       Er staan drie knoppen zodra een voorbeeld speelt, en die pasten niet in een
       smalle kaart. Met justify-content:flex-end spilt de overloop naar LINKS,
       dus de knop Voorbeeld stoppen liep de kaart uit — gemeten: 67 px buiten
       de linkerrand bij een kaart van 244 px.

       Waarom wikkelen en niet een korter label: een korter label (Stoppen)
       verliest betekenis naast Annuleren en Opslaan — stoppen wát? — en het helpt
       maar tot de volgende lettergrootte. Wikkelen werkt bij elke breedte en bij
       elke tekstgrootte, ook die van een gebruiker die groot leest.

       flex:0 0 auto erbij: zonder dat knijpt flexbox de knoppen eerst plat
       vóór hij wikkelt, en dan staat de tekst tegen de rand van zijn eigen knop. */
    .voet {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
      padding: 12px 16px;
    }
    .voet button {
      flex: 0 0 auto;
    }
    .voet .voorbeeld {
      margin-right: auto;
    }
  `);var Ke="person",St="Kies een persoon in de kaartinstellingen.",Ge="De gekozen persoon bestaat niet meer.",Ct="De opgeslagen wekkers van deze persoon zijn onleesbaar.",bn=Object.freeze(["grid_options","layout_options","view_layout","visibility"]);function Be(n){if(!n||typeof n!="object"||Array.isArray(n))throw new Error("De kaartconfig ontbreekt of is geen object.");let e=n.person;if(e==null||e==="")return{...n};if(typeof e!="string")throw new Error("'person' moet een entity-ID zijn, zoals person.sven.");if(!e.startsWith(`${Ke}.`))throw new Error(`'${e}' zit niet in het domein ${Ke}. Kies een persoon, zoals person.sven.`);return{...n}}function Ze(n){return{type:`custom:${n}`}}function Fe(n,e){return n?e?{soort:"ok",tekst:null,isFout:!1}:{soort:"weg",tekst:Ge,isFout:!0}:{soort:"ontbreekt",tekst:St,isFout:!1}}function qe(n,e){return n==="not_found"?Ge:n==="home_assistant_error"?Ct:e||"Er ging iets mis bij het ophalen van de wekkers."}var Tt="home-assistant";function Ye({leesRegistry:n,definities:e,waarschuw:t=()=>{},plan:i=(d,a)=>setTimeout(d,a),nu:s=()=>Date.now(),marker:o=Tt,intervalMs:r=20,maxWachtMs:h=1e4}){let d=s();function a(){let g=n();if(!g)return!1;for(let[m,j]of e)try{g.get(m)||g.define(m,j)}catch(me){t(`kon ${m} niet registreren: ${me&&me.message}`)}return!0}function u(){let g=n();return!g||!g.get(o)?!1:a()}if(u())return!0;let c=()=>{if(!u()){if(s()-d>=h){t(`${o} is na ${h} ms niet verschenen; de kaart wordt alsnog geregistreerd`),a();return}i(c,r)}};return i(c,r),!1}var Ot=["ma","di","wo","do","vr","za","zo"],Nt="Geen wekkers ingesteld",Vt="Eenmalig",Dt="Eenmalig \u2014 afgelopen",Ht="Geen wekker actief",Je="Stoppen",Mt="Er is een melding over deze wekker, maar de tekst ontbreekt.";function Pt(n){return!Array.isArray(n)||n.length===0?Vt:[...new Set(n)].sort((t,i)=>t-i).map(t=>Ot[t-1]??"?").join(" ")}function Rt(n,e){return!n||Array.isArray(n.days)&&n.days.length>0?!1:Date.parse(n?.one_shot_at??"")<=e}function Xe(n,e){return Rt(n,e)?Dt:Pt(n?.days)}function Qe(n){let e=n?.last_message;return!e||typeof e!="object"||Array.isArray(e)?null:{tekst:typeof e.text=="string"&&e.text.trim()?e.text:Mt,severity:e.severity==="error"?"error":"notice",isFout:e.severity==="error",kind:typeof e.kind=="string"?e.kind:null}}function et(n){let e=n?.alarms;if(!Array.isArray(e)||e.length===0)return Nt;let t=n?.next_fire?.text;return typeof t=="string"&&t.trim()?t:Ht}function tt(n,e){let t=[...new Set((e??[]).filter(r=>typeof r=="string"))];if(t.length===0)return null;let i=t.map(r=>(n??[]).find(h=>h?.id===r)).filter(Boolean),s=i.map(r=>r.name).filter(Boolean),o=[...new Set(i.map(r=>r.time).filter(Boolean))];return{ids:t,naam:s.length?s.join(" en "):"Wekker",tijd:o.join(" en ")}}var Lt="1.0.4",Ut="M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z",It="M9,3V4H4V6H5V19A2,2 0 0,0 7,21H17A2,2 0 0,0 19,19V6H20V4H15V3H9M7,6H17V19H7V6M9,8V17H11V8H9M13,8V17H15V8H13Z",nt="M13,9H11V7H13M13,17H11V11H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z",Wt="M13,14H11V9H13M13,18H11V16H13M1,21H23L12,2L1,21Z",J=(n,e="icoon")=>p`<svg class=${e} viewBox="0 0 24 24" aria-hidden="true">
    <path d=${n} />
  </svg>`,W=class extends v{constructor(){super(),this._toestand=null,this._fout=null,this._bevestigVoor=null,this._bezig=!1,this._tijdelijkeMelding=null,this._editorVoor=void 0,this._entiteiten=null,this._abonnementVoor=null,this._afmelden=null}setConfig(e){let t=Be(e),i=t.person!==this._config?.person;this._config=t,i&&(this._toestand=null,this._fout=null,this._bevestigVoor=null,this._herstartAbonnement())}static getConfigElement(){return document.createElement(he)}static getStubConfig(){return Ze(x)}getGridOptions(){return{rows:"auto",columns:12,min_columns:6}}getCardSize(){if(this._stop())return 3;let e=this._toestand?.alarms?.length??0;return 1+Math.max(e,1)}connectedCallback(){super.connectedCallback(),this._herstartAbonnement()}disconnectedCallback(){super.disconnectedCallback(),this._stopAbonnement()}updated(e){e.has("hass")&&this.hass&&this._startAbonnement()}async _startAbonnement(){let e=this._config?.person;if(!(!this.hass||!e||!this.isConnected)&&this._abonnementVoor!==e){this._abonnementVoor=e;try{let t=await this.hass.connection.subscribeMessage(i=>this._opGebeurtenis(i),{type:f.subscribe,person:e});if(this._abonnementVoor!==e){t();return}this._afmelden=t}catch(t){console.warn(`${x}: abonneren mislukt: ${t?.message??t}`)}await this._haalOp()}}_stopAbonnement(){if(this._afmelden){try{this._afmelden()}catch(e){console.warn(`${x}: afmelden mislukt: ${e?.message??e}`)}this._afmelden=null}this._abonnementVoor=null}_herstartAbonnement(){this._stopAbonnement(),this._startAbonnement()}_opGebeurtenis(e){let t=e?.alarm_id,i=e?.event;if(typeof t=="string"&&this._toestand){let s=new Set(this._toestand.ringing??[]);i==="started"?s.add(t):s.delete(t),this._toestand={...this._toestand,ringing:[...s]}}this._haalOp()}async _haalOp(){let e=this._config?.person;if(!(!this.hass||!e))try{let t=await this.hass.callWS({type:f.get,person:e});if(this._config?.person!==e)return;this._toestand=t,this._fout=null}catch(t){if(this._config?.person!==e)return;this._toestand=null,this._fout=qe(t?.code,t?.message)}}async _roep(e){if(!(!this.hass||this._bezig)){this._bezig=!0;try{let t=await this.hass.callWS(e);t&&typeof t=="object"&&(this._toestand=t,this._fout=null)}catch(t){this._toon(t?.message??"De opdracht is niet gelukt.")}finally{this._bezig=!1}}}async _openEditor(e){if(this._bevestigVoor=null,this._editorVoor=e,!!this.hass)try{this._entiteiten=await this.hass.callWS({type:f.entities})}catch(t){this._entiteiten=null,console.warn(`${x}: entiteitenlijst ophalen mislukt: ${t?.message??t}`)}}_sluitEditor(){this._editorVoor=void 0}_toon(e){this._tijdelijkeMelding=e,clearTimeout(this._meldingTimer),this._meldingTimer=setTimeout(()=>{this._tijdelijkeMelding=null},6e3)}_person(){return this._config?.person}_zetAan(e,t){this._roep({type:f.setEnabled,person:this._person(),alarm_id:e.id,enabled:t})}_verwijder(e){this._bevestigVoor=null,this._roep({type:f.delete,person:this._person(),alarm_id:e.id})}_begrepen(e){this._roep({type:f.clearMessage,person:this._person(),alarm_id:e.id})}async _stopAlles(e){for(let t of e)await this._roep({type:f.stop,person:this._person(),alarm_id:t})}_stop(){return this._toestand?tt(this._toestand.alarms,this._toestand.ringing):null}render(){if(!this._config)return l;let e=this._config.person,t=!!(e&&this.hass?.states?.[e]),i=Fe(e,t);if(i.soort!=="ok")return this._mededeling(i.tekst,i.isFout);if(this._fout)return this._mededeling(this._fout,!0);if(!this._toestand)return this._mededeling("Wekkers ophalen\u2026",!1);let s=this._stop();return this._editorVoor!==void 0&&!s?p`<ha-card>
        <domotiapp-alarm-editor
          .hass=${this.hass}
          .person=${this._config.person}
          .wekker=${this._editorVoor}
          .entiteiten=${this._entiteiten}
          @editor-dicht=${()=>this._sluitEditor()}
          @editor-opgeslagen=${o=>{this._toestand=o.detail.toestand,this._sluitEditor()}}
        ></domotiapp-alarm-editor>
      </ha-card>`:p`<ha-card>
      ${s?this._stopknop(s):this._lijst()}
      ${this._tijdelijkeMelding?p`<div class="onderrij">
            ${J(nt,"icoon klein")}
            <span class="boodschap">${this._tijdelijkeMelding}</span>
          </div>`:l}
    </ha-card>`}_mededeling(e,t){return p`<ha-card>
      <div class="mededeling ${t?"fout":""}">${e}</div>
    </ha-card>`}_stopknop(e){return p`<button
      class="stopknop"
      @click=${()=>this._stopAlles(e.ids)}
    >
      <div class="stop-tijd">${e.tijd}</div>
      <div class="stop-naam">${e.naam}</div>
      <div class="stop-woord">${Je}</div>
    </button>`}_lijst(){let e=this._toestand.alarms??[],t=Date.now();return p`
      <div class="kop ${e.length===0?"leeg":""}">
        <span class="volgende">${et(this._toestand)}</span>
        <button
          class="icoonknop"
          title="Wekker toevoegen"
          aria-label="Wekker toevoegen"
          @click=${()=>this._openEditor(null)}
        >
          ${J(Ut)}
        </button>
      </div>
      ${e.map(i=>this._rij(i,t))}
    `}_bevestiging(e){return p`<div class="onderrij bevestiging">
      <span class="boodschap">${He(e)}</span>
      <button
        class="tekstknop"
        @click=${()=>{this._bevestigVoor=null}}
      >
        Annuleren
      </button>
      <button class="tekstknop gevaar" @click=${()=>this._verwijder(e)}>
        Verwijderen
      </button>
    </div>`}_rij(e,t){let i=Qe(e),s=!!e.enabled;return p`
      <div class="rij ${s?"":"uit"}">
        <button
          class="tikvlak"
          type="button"
          aria-label="Wekker ${e.name} bewerken"
          @click=${()=>this._openEditor(e)}
        >
          <div class="tijd">${e.time}</div>
          <div class="tekst">
            <div class="naam">${e.name}</div>
            <div class="sub">${Xe(e,t)}</div>
          </div>
        </button>
        <button
          class="schakelaar"
          role="switch"
          aria-checked=${s?"true":"false"}
          aria-label="Wekker ${e.name} aan of uit"
          @click=${()=>this._zetAan(e,!s)}
        ></button>
        <button
          class="icoonknop"
          title="Verwijderen"
          aria-label="Wekker ${e.name} verwijderen"
          @click=${()=>{this._bevestigVoor=e.id}}
        >
          ${J(It)}
        </button>
      </div>
      ${this._bevestigVoor===e.id?this._bevestiging(e):l}
      ${i?p`<div class="onderrij ${i.isFout?"fout":""}">
            ${J(i.isFout?Wt:nt,"icoon klein")}
            <span class="boodschap">${i.tekst}</span>
            <button class="tekstknop" @click=${()=>this._begrepen(e)}>
              Begrepen
            </button>
          </div>`:l}
    `}};b(W,"properties",{hass:{attribute:!1},_config:{state:!0},_toestand:{state:!0},_fout:{state:!0},_bevestigVoor:{state:!0},_bezig:{state:!0},_tijdelijkeMelding:{state:!0},_editorVoor:{state:!0},_entiteiten:{state:!0}}),b(W,"styles",S`
    /* unsafeCSS en niet de constante rechtstreeks: lit weigert een gewone
       string in een css-template en gooit dan — op modulescope, wat SPEC 19.4
       verbiedt. De waarde is onze eigen constante en komt nergens van buiten. */
    :host {
      --domotiapp-accent: ${z(F)};
      /* De kaart meet zich aan zijn eigen breedte en niet aan het venster: in een
         bubble pop-up is de kaart smal terwijl het venster breed is. Gemeten in
         fase 8 bij 244 px: de naam werd tot een enkele letter platgeknepen en de
         dagen stapelden verticaal.

         display:block is hier GEEN opmaakvoorkeur maar een voorwaarde. Gemeten:
         HA geeft de kaarthost display:inline, en op een inline element doet
         container-type niets — de host wordt dan geen query-container en de
         regels hieronder komen nooit aan bod.

         En de container heeft een NAAM. Zonder naam kiest de browser de
         dichtstbijzijnde container-voorouder, en dat kan er een van HA zelf zijn;
         dan hangt onze opmaak af van de afmeting van iets waar wij niet over
         gaan. */
      display: block;
      container: domotiapp-kaart / inline-size;
    }
    /* Geen overflow:hidden op de kaart: de stopknop houdt daarom zelf de
       hoekafronding van de kaart. Er staat sinds fase 7 niets meer boven de kaart
       te zweven — de volle-viewportlaag die het overloopmenu afsloot, is precies
       wat die knoppen onklikbaar maakte. */
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
      flex: 0 0 auto;
    }
    /* Onder de 300 px is er geen ruimte voor 28 px cijfers naast een naam, een
       schakelaar en een prullenbak. Kleinere cijfers zijn dan beter dan een naam
       van een letter. */
    @container domotiapp-kaart (max-width: 300px) {
      .tijd {
        font-size: 22px;
        min-width: 62px;
      }
      .rij {
        gap: 8px;
        padding: 10px 12px;
      }
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

    /* --- melding en bevestiging op een rij ---

       WIKKELT, sinds fase 9. Gemeten in een échte Bubble Card-pop-up op 390 px —
       telefoonbreedte, de conditie waarin de klant hem gebruikt — met een wekker
       die "Zaterdagochtendzwemtraining" heet: de knop "Verwijderen" stak 27 px
       buiten de kaart en 9 px buiten de pop-up, en dat laatste betekent dat een
       deel van hem niet meer aan te wijzen is. Met een korte naam gebeurt het
       onder een kaartbreedte van 276 px.

       Waarom het niet opviel: .boodschap had flex 1, dus min-width auto,
       en dan kan de tekst niet onder zijn langste woord krimpen. De rij liep over
       en duwde de knoppen naar rechts naar buiten. Fase 8 heeft dit voor .voet
       en de zoekrij opgelost maar deze rij niet meegenomen, omdat de meting de
       bevestiging nooit heeft geopend.

       Dat het uitgerekend de knop van een ONOMKEERBARE handeling is die wegvalt,
       is de reden dat dit geen schoonheidsfoutje is. */
    .onderrij {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      padding: 0 16px 12px 16px;
      border-bottom: 1px solid var(--divider-color);
      font-size: var(--ha-font-size-s, 12px);
    }
    .onderrij .boodschap {
      /* Een ondergrens in plaats van flex 1: onder de 8em gaan de knoppen naar
         de volgende regel in plaats van dat ze de rij uit worden geduwd. */
      flex: 1 1 8em;
      /* min-width 0 haalt de impliciete ondergrens van de flexitem weg en
         overflow-wrap breekt een naam die zelf breder is dan de kaart — een
         wekkernaam is invoer van de klant en heeft geen bovengrens. */
      min-width: 0;
      overflow-wrap: anywhere;
      color: var(--secondary-text-color);
    }
    .onderrij.fout .boodschap,
    .onderrij.fout .icoon {
      color: var(--error-color);
    }
    button.tekstknop {
      /* Hier stond in de eerste opzet van fase 9 een flex 0 0 auto, geleend van de
         voetregel in de editor (fase 8). De mutatieproef wees uit dat die regel
         hier NIETS doet: hem terugzetten op de standaard 0 1 auto veranderde bij
         390, 244 én 180 px geen enkele positie. De reden is de white-space
         hieronder — een knop die niet mag afbreken kan door flexbox niet onder
         zijn tekstbreedte geknepen worden, dus er valt niets te krimpen. Volgens
         valkuil 34, derde rij, gaat zo'n regel eruit in plaats van dat er een
         test bij verzonnen wordt. */
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

    /* De bevestigingsregel mag niet in het niets opgaan tussen de wekkers: hij
       vraagt iets onomkeerbaars. Zelfde vorm als een melding, met de tekst in de
       primaire kleur in plaats van de secundaire. */
    .onderrij.bevestiging .boodschap {
      color: var(--primary-text-color);
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
      /* width 100% met eigen padding van 16 px links en rechts — dezelfde vorm die
         in fase 10 op iOS bij het tijdveld misging. Chrome geeft een button
         border-box uit zijn UA-stylesheet (gemeten in de stoptoestand: 352 px
         getekend bij 352 px beschikbaar), maar op die standaard willen we niet
         leunen bij de knop die de wekker uitzet. */
      box-sizing: border-box;
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
  `);var N=class N extends v{constructor(){super(...arguments);b(this,"_label",t=>t.name==="person"?"Persoon":t.name)}setConfig(t){this._config={...t}}render(){return!this._config||!this.hass?l:p`
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
    `}_gewijzigd(t){t.stopPropagation();let i={...this._config,...t.detail.value};this.dispatchEvent(new CustomEvent("config-changed",{detail:{config:i},bubbles:!0,composed:!0}))}};b(N,"properties",{hass:{attribute:!1},_config:{state:!0}}),b(N,"styles",S`
    .uitleg {
      padding: 0 0 12px 0;
      color: var(--secondary-text-color);
      font-size: var(--ha-font-size-s, 12px);
    }
  `),b(N,"_SCHEMA",[{name:"person",required:!0,selector:{entity:{filter:{domain:"person"}}}}]);var ge=N;Ye({leesRegistry:()=>globalThis.customElements,definities:[[x,W],[he,ge],[Ne,O]],waarschuw:n=>console.warn(`${x}: ${n}`)});window.customCards=window.customCards||[];window.customCards.some(n=>n.type===x)||window.customCards.push({type:x,name:Ve,description:`Wekkerkaart van DomotiApp (v${Lt}).`,preview:!1,documentationURL:De});
