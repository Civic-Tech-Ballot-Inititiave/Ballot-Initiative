import streamlit as st

st.set_page_config(
    page_title="Home",
    page_icon="🗳️",
)

st.write("# Welcome to the Ballot Initiative Project! 👋")

st.sidebar.success("👆Visit the Petition Validation page to get started.")

st.markdown(
    """

    This project aims to

    > *Provide a cheap, quick, and accurate way to validate signed petitions for local ballot measures*

    It does this by performing [OCR](https://en.wikipedia.org/wiki/Optical_character_recognition) on the signatures, matching the results against official voter records, and providing a score for each signature. 
    """
)

st.image("app/ballot_initiative_schematic.png", caption="Core process for validating signatures", use_container_width=True)

st.markdown(
    """    
Signature verification is typically a tedious process that requires human reviewers to inspect submitted signatures one by one, searching a voter database for the associated voter, and then ensuring the voter was registered at the time of signing. This process requires hundreds of person-hours and takes resources away from the more impactful work of advocating for the ballot measures themselves. 

There is available software that can perform signature verification, but it is generally expensive and inaccessible to more grassroots organizations. So by providing a cheap and easy way to automate this process, we hope to help even the smallest organizations get their ballot measures off the ground.

 ### The Builders
 This project was built by the members of [Civic Tech DC](https://www.civictechdc.org/), a group of tech-savvy volunteers passionate about building software for the public good. 

 Because of our experience with the DC ballot initiative process, we built the current version of the application for **Washington DC petitions of the type [here](https://github.com/Civic-Tech-Ballot-Inititiave/Ballot-Initiative/blob/main/sample_data/fake_signed_petitions_1-10.pdf)**. However, the code is open source and it is easy to modify itfor your use case. Contact the Civic Tech DC team if you have questions about implementing it for your organization.


 ### Want to learn more?
 - Check out the project repository [(Ballot Initiative Repository)](https://github.com/Civic-Tech-Ballot-Inititiave/Ballot-Initiative)
 - Ballot Initiatives around the US [(Ballotpedia)](https://ballotpedia.org/Ballot_initiative)
 - Civic Tech DC Homepage [(Civic Tech DC)](https://www.civictechdc.org/)
"""
)
# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>"
    "© 2024 Ballot Initiative Project | "
    "<a href='#'>Privacy Policy</a> | "
    "<a href='#'>Terms of Use</a>"
    "</div>", 
    unsafe_allow_html=True
)
